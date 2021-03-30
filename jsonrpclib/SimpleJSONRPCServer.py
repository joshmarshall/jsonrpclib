import logging
import os
import socket
import socketserver
import sys
import traceback
import xmlrpc.server

try:
    import fcntl
except ImportError:
    # For Windows
    fcntl = None

import jsonrpclib
from jsonrpclib import Fault
from jsonrpclib.jsonrpc import USE_UNIX_SOCKETS


def get_version(request):
    # must be a dict
    if 'jsonrpc' in request.keys():
        return 2.0
    if 'id' in request.keys():
        return 1.0
    return None


def validate_request(request):
    if not isinstance(request, dict):
        fault = Fault(
            -32600, 'Request must be {}, not %s.' % type(request)
        )
        return fault
    rpcid = request.get('id', None)
    version = get_version(request)
    if not version:
        fault = Fault(-32600, 'Request %s invalid.' % request, rpcid=rpcid)
        return fault
    request.setdefault('params', [])
    method = request.get('method', None)
    params = request.get('params')
    if not method or not isinstance(method, str) or \
            not isinstance(params, (list, dict, tuple)):
        fault = Fault(
            -32600, 'Invalid request parameters or method.', rpcid=rpcid
        )
        return fault
    return True


class SimpleJSONRPCDispatcher(xmlrpc.server.SimpleXMLRPCDispatcher):

    def __init__(self, encoding=None):
        xmlrpc.server.SimpleXMLRPCDispatcher.__init__(
            self, allow_none=True, encoding=encoding)

    def _marshaled_dispatch(self, data, dispatch_method=None):
        response = None
        try:
            request = jsonrpclib.loads(data)
        except Exception as e:
            fault = Fault(-32700, 'Request %s invalid. (%s)' % (data, e))
            response = fault.response()
            return response
        if not request:
            fault = Fault(-32600, 'Request invalid -- no request data.')
            return fault.response()
        if isinstance(request, list):
            # This SHOULD be a batch, by spec
            responses = []
            for req_entry in request:
                result = validate_request(req_entry)
                if type(result) is Fault:
                    responses.append(result.response())
                    continue
                resp_entry = self._marshaled_single_dispatch(req_entry)
                if resp_entry is not None:
                    responses.append(resp_entry)
            if len(responses) > 0:
                response = '[%s]' % ','.join(responses)
            else:
                response = ''
        else:
            result = validate_request(request)
            if type(result) is Fault:
                return result.response()
            response = self._marshaled_single_dispatch(request)
        return response

    def _marshaled_single_dispatch(self, request):
        # TODO - Use the multiprocessing and skip the response if
        # it is a notification
        # Put in support for custom dispatcher here
        # (See SimpleXMLRPCServer._marshaled_dispatch)
        method = request.get('method')
        params = request.get('params')
        try:
            response = self._dispatch(method, params)
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            fault = Fault(-32603, '%s:%s' % (exc_type, exc_value))
            return fault.response()
        if 'id' not in request.keys() or request['id'] is None:
            # It's a notification
            return None
        try:
            response = jsonrpclib.dumps(response,
                                        methodresponse=True,
                                        rpcid=request['id']
                                        )
            return response
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            fault = Fault(-32603, '%s:%s' % (exc_type, exc_value))
            return fault.response()

    def _dispatch(self, method, params):
        func = None
        try:
            func = self.funcs[method]
        except KeyError:
            if self.instance is not None:
                if hasattr(self.instance, '_dispatch'):
                    return self.instance._dispatch(method, params)
                else:
                    try:
                        func = xmlrpc.server.resolve_dotted_attribute(
                            self.instance,
                            method,
                            True
                            )
                    except AttributeError:
                        pass
        if func is not None:
            try:
                if isinstance(params, list):
                    response = func(*params)
                else:
                    response = func(**params)
                return response
            # except TypeError:
            #     return Fault(-32602, 'Invalid parameters.')
            except Exception:
                err_lines = traceback.format_exc().splitlines()
                trace_string = '%s | %s' % (err_lines[-3], err_lines[-1])
                fault = jsonrpclib.Fault(-32603, 'Server error: %s' %
                                         trace_string)
                return fault
        else:
            return Fault(-32601, 'Method %s not supported.' % method)


class SimpleJSONRPCRequestHandler(
        xmlrpc.server.SimpleXMLRPCRequestHandler):

    def do_POST(self):
        if not self.is_rpc_path_valid():
            self.report_404()
            return
        try:
            max_chunk_size = 10*1024*1024
            size_remaining = int(self.headers["content-length"])
            L = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                chunk = self.rfile.read(chunk_size).decode()
                L.append(chunk)
                size_remaining -= len(L[-1])
            data = ''.join(L)
            response = self.server._marshaled_dispatch(data)
            self.send_response(200)
        except Exception:
            self.send_response(500)
            err_lines = traceback.format_exc().splitlines()
            trace_string = '%s | %s' % (err_lines[-3], err_lines[-1])
            fault = jsonrpclib.Fault(-32603, 'Server error: %s' % trace_string)
            response = fault.response()
        if response is None:
            response = ''
        self.send_header("Content-type", "application/json-rpc")
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        if isinstance(response, bytes):
            self.wfile.write(response)
        else:
            self.wfile.write(response.encode())
        self.wfile.flush()
        self.connection.shutdown(1)


class SimpleJSONRPCUnixRequestHandler(SimpleJSONRPCRequestHandler):

    disable_nagle_algorithm = False


class SimpleJSONRPCServer(socketserver.TCPServer, SimpleJSONRPCDispatcher):

    allow_reuse_address = True

    def __init__(self, addr, requestHandler=SimpleJSONRPCRequestHandler,
                 logRequests=True, encoding=None, bind_and_activate=True,
                 address_family=socket.AF_INET):
        self.logRequests = logRequests
        SimpleJSONRPCDispatcher.__init__(self, encoding)
        self.address_family = address_family

        if USE_UNIX_SOCKETS and address_family == socket.AF_UNIX:
            # Unix sockets can't be bound if they already exist in the
            # filesystem. The convention of e.g. X11 is to unlink
            # before binding again.
            if os.path.exists(addr):
                try:
                    os.unlink(addr)
                except OSError:
                    logging.warning("Could not unlink socket %s", addr)

            if requestHandler == SimpleJSONRPCRequestHandler:
                requestHandler = SimpleJSONRPCUnixRequestHandler

        socketserver.TCPServer.__init__(
            self, addr, requestHandler, bind_and_activate)
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)


class CGIJSONRPCRequestHandler(SimpleJSONRPCDispatcher):

    def __init__(self, encoding=None):
        SimpleJSONRPCDispatcher.__init__(self, encoding)

    def handle_jsonrpc(self, request_text):
        response = self._marshaled_dispatch(request_text)
        print('Content-Type: application/json-rpc')
        print('Content-Length: %d' % len(response))
        print()
        sys.stdout.write(response)

    handle_xmlrpc = handle_jsonrpc

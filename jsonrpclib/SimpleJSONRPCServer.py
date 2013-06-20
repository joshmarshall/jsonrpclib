#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Defines a request dispatcher, a HTTP request handler, a HTTP server and a
CGI request handler.
"""

__version__ = "0.1.5"

# ------------------------------------------------------------------------------
# Local modules
from jsonrpclib import Fault, config
import jsonrpclib
import jsonrpclib.utils as utils

# Standard library
import socket
import sys
import traceback

try:
    import fcntl
except ImportError:
    # For Windows
    fcntl = None

# ------------------------------------------------------------------------------

if sys.version_info[0] < 3:
    # Python 2
    import SimpleXMLRPCServer as xmlrpcserver
    import SocketServer as socketserver

else:
    # Python 3
    import xmlrpc.server as xmlrpcserver
    import socketserver

# ------------------------------------------------------------------------------

def get_version(request):
    """
    Computes the JSON-RPC version
    
    :param request: A request dictionary
    :return: The JSON-RPC version or None
    """
    if 'jsonrpc' in request:
        return 2.0

    elif 'id' in request:
        return 1.0

    return None


def validate_request(request):
    """
    Validates the format of a request dictionary
    
    :param request: A request dictionary
    :return: True if the dictionary is valid, else a Fault object
    """
    if not isinstance(request, utils.DictType):
        # Invalid request type
        return Fault(-32600, 'Request must be a dict, not {0}' \
                     .format(type(request).__name__))

    # Get the request ID
    rpcid = request.get('id', None)

    # Check request version
    version = get_version(request)
    if not version:
        return Fault(-32600, 'Request {0} invalid.'.format(request),
                     rpcid=rpcid)

    # Default parameters: empty list
    request.setdefault('params', [])

    # Check parameters
    method = request.get('method', None)
    params = request.get('params')
    param_types = (utils.ListType, utils.DictType, utils.TupleType)

    if not method or not isinstance(method, utils.StringTypes) or \
    not isinstance(params, param_types):
        # Invalid type of method name or parameters
        return Fault(-32600, 'Invalid request parameters or method.',
                     rpcid=rpcid)

    # Valid request
    return True

# ------------------------------------------------------------------------------

class NoMulticallResult(Exception):
    """
    No result in multicall
    """
    pass


class SimpleJSONRPCDispatcher(xmlrpcserver.SimpleXMLRPCDispatcher):

    def __init__(self, encoding=None):
        """
        Sets up the dispatcher with the given encoding.
        None values are allowed.
        """
        if not encoding:
            # Default encoding
            encoding = "UTF-8"

        xmlrpcserver.SimpleXMLRPCDispatcher.__init__(self,
                                                     allow_none=True,
                                                     encoding=encoding)


    def _unmarshaled_dispatch(self, request, dispatch_method=None):
        """
        Loads the request dictionary (unmarshaled), calls the method(s)
        accordingly and returns a JSON-RPC dictionary (not marshaled)
        
        :param request: JSON-RPC request dictionary (or list of)
        :param dispatch_method: Custom dispatch method (for method resolution)
        :return: A JSON-RPC dictionary (or an array of) or None if the request
                 was a notification
        :raise NoMulticallResult: No result in batch
        """
        if not request:
            # Invalid request dictionary
            fault = Fault(-32600, 'Request invalid -- no request data.')
            return fault.dump()

        if type(request) is utils.ListType:
            # This SHOULD be a batch, by spec
            responses = []
            for req_entry in request:
                # Validate the request
                result = validate_request(req_entry)
                if type(result) is Fault:
                    responses.append(result.dump())
                    continue

                # Call the method
                resp_entry = self._marshaled_single_dispatch(req_entry,
                                                             dispatch_method)

                # Store its result
                if isinstance(resp_entry, Fault):
                    responses.append(resp_entry.dump())

                elif resp_entry is not None:
                    responses.append(resp_entry)

            if len(responses) == 0:
                # No non-None result
                raise NoMulticallResult("No result")

            return responses

        else:
            # Single call
            result = validate_request(request)
            if type(result) is Fault:
                return result.dump()

            # Call the method
            response = self._marshaled_single_dispatch(request, dispatch_method)

            if isinstance(response, Fault):
                return response.dump()

            return response


    def _marshaled_dispatch(self, data, dispatch_method=None):
        """
        Parses the request data (marshaled), calls method(s) and returns a
        JSON string (marshaled)
        
        :param data: A JSON request string
        :param dispatch_method: Custom dispatch method (for method resolution)
        :return: A JSON-RPC response string (marshaled)
        """
        # Parse the request
        try:
            request = jsonrpclib.loads(data)

        except Exception as ex:
            # Parsing/loading error
            fault = Fault(-32700, 'Request {0} invalid. ({1}:{2})' \
                          .format(data, type(ex).__name__, ex))
            return fault.response()

        # Get the response dictionary
        try:
            response = self._unmarshaled_dispatch(request, dispatch_method)

            if response is not None:
                # Compute the string representation of the dictionary/list
                return jsonrpclib.jdumps(response, self.encoding)

            else:
                # No result (notification)
                return ''

        except NoMulticallResult:
            # Return an empty string (jsonrpclib internal behaviour)
            return ''


    def _marshaled_single_dispatch(self, request, dispatch_method=None):
        """
        Dispatches a single method call
        
        :param request: A validated request dictionary
        :param dispatch_method: Custom dispatch method (for method resolution)
        :return: A JSON-RPC response dictionary, or None if it was a
                 notification request
        """
        # TODO - Use the multiprocessing and skip the response if
        # it is a notification
        method = request.get('method')
        params = request.get('params')
        try:
            # Call the method
            if dispatch_method is not None:
                response = dispatch_method(method, params)
            else:
                response = self._dispatch(method, params)

        except:
            # Return a fault
            exc_type, exc_value, _ = sys.exc_info()
            fault = Fault(-32603, '{0}:{1}'.format(exc_type, exc_value))
            return fault.dump()

        if 'id' not in request or request['id'] in (None, ''):
            # It's a notification, no result needed
            # Do not use 'not id' as it might be the integer 0
            return None

        # Prepare a JSON-RPC dictionary
        try:
            return jsonrpclib.dump(response, rpcid=request['id'],
                                   is_response=True)

        except:
            # JSON conversion exception
            exc_type, exc_value, _ = sys.exc_info()
            fault = Fault(-32603, '{0}:{1}'.format(exc_type, exc_value))
            return fault.dump()


    def _dispatch(self, method, params):
        """
        Default method resolver and caller
        
        :param method: Name of the method to call
        :param params: List of arguments to give to the method
        :return: The result of the method
        """
        func = None
        try:
            # Try with registered methods
            func = self.funcs[method]

        except KeyError:
            if self.instance is not None:
                # Try with the registered instance
                if hasattr(self.instance, '_dispatch'):
                    # Instance has a custom dispatcher
                    return self.instance._dispatch(method, params)

                else:
                    # Resolve the method name in the instance
                    try:
                        func = xmlrpcserver.resolve_dotted_attribute(\
                                                self.instance, method, True)
                    except AttributeError:
                        # Unknown method
                        pass

        if func is not None:
            try:
                # Call the method
                if type(params) is utils.ListType:
                    return func(*params)

                else:
                    return func(**params)

            except TypeError as ex:
                # Maybe the parameters are wrong
                return Fault(-32602, 'Invalid parameters: {0}'.format(ex))

            except:
                # Method exception
                err_lines = traceback.format_exc().splitlines()
                trace_string = '{0} | {1}'.format(err_lines[-3], err_lines[-1])
                return Fault(-32603, 'Server error: {0}'.format(trace_string))

        else:
            # Unknown method
            return Fault(-32601, 'Method {0} not supported.'.format(method))

# ------------------------------------------------------------------------------

class SimpleJSONRPCRequestHandler(xmlrpcserver.SimpleXMLRPCRequestHandler):
    """
    HTTP server request handler
    """
    def do_POST(self):
        """
        Handles POST requests
        """
        if not self.is_rpc_path_valid():
            self.report_404()
            return

        try:
            # Read the request body
            max_chunk_size = 10 * 1024 * 1024
            size_remaining = int(self.headers["content-length"])
            chunks = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                chunks.append(utils.from_bytes(self.rfile.read(chunk_size)))
                size_remaining -= len(chunks[-1])
            data = ''.join(chunks)

            # Execute the method
            response = self.server._marshaled_dispatch(data)

            # No exception: send a 200 OK
            self.send_response(200)

        except Exception:
            # Exception: send 500 Server Error
            self.send_response(500)
            err_lines = traceback.format_exc().splitlines()
            trace_string = '{0} | {1}'.format(err_lines[-3], err_lines[-1])
            fault = jsonrpclib.Fault(-32603, 'Server error: {0}'\
                                     .format(trace_string))
            response = fault.response()

        if response is None:
            # Avoid to send None
            response = ''

        # Convert the response to the valid string format
        response = utils.to_bytes(response)

        # Send it
        self.send_header("Content-type", config.content_type)
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
        self.wfile.flush()
        self.connection.shutdown(1)

# ------------------------------------------------------------------------------

class SimpleJSONRPCServer(socketserver.TCPServer, SimpleJSONRPCDispatcher):
    """
    JSON-RPC server (and dispatcher)
    """
    # This simplifies server restart after error
    allow_reuse_address = True

    def __init__(self, addr, requestHandler=SimpleJSONRPCRequestHandler,
                 logRequests=True, encoding=None, bind_and_activate=True,
                 address_family=socket.AF_INET):
        """
        Sets up the server and the dispatcher
        
        :param addr: The server listening address
        :param requestHandler: Custom request handler
        :param logRequests: Flag to(de)activate requests logging
        :param encoding: The dispatcher request encoding
        :param bind_and_activate: If True, starts the server immediately
        :param address_family: The server listening address family
        """
        # Set up the dispatcher fields
        SimpleJSONRPCDispatcher.__init__(self, encoding)

        # Prepare the server configuration
        self.logRequests = logRequests
        self.address_family = address_family

        # Set up the server
        socketserver.TCPServer.__init__(self, addr, requestHandler,
                                        bind_and_activate)

        # Windows-specific
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)

# ------------------------------------------------------------------------------

class CGIJSONRPCRequestHandler(SimpleJSONRPCDispatcher):
    """
    JSON-RPC CGI handler (and dispatcher)
    """
    def __init__(self, encoding=None):
        """
        Sets up the dispatcher
        
        :param encoding: Dispatcher encoding
        """
        SimpleJSONRPCDispatcher.__init__(self, encoding)

    def handle_jsonrpc(self, request_text):
        """
        Handle a JSON-RPC request
        """
        response = self._marshaled_dispatch(request_text)
        sys.stdout.write('Content-Type: {0}\r\n'.format(config.content_type))
        sys.stdout.write('Content-Length: {0:d}\r\n'.format(len(response)))
        sys.stdout.write('\r\n')
        sys.stdout.write(response)

    # XML-RPC alias
    handle_xmlrpc = handle_jsonrpc

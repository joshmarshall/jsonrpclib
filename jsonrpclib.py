"""
JSONRPCLIB -- started by Josh Marshall

This library is a JSON-RPC v.2 (proposed) implementation which
follows the xmlrpclib API for portability between clients. It
uses the same Server / ServerProxy, loads, dumps, etc. syntax,
while providing features not present in XML-RPC like:

* Keyword arguments
* Notifications
* Versioning
* Batches and batch notifications

Eventually, I'll add a SimpleXMLRPCServer compatible library,
and other things to tie the thing off nicely. :)

For a quick-start, just open a console and type the following,
replacing the server address, method, and parameters 
appropriately.
>>> import jsonrpclib
>>> server = jsonrpclib.Server('http://localhost:8181')
>>> server.add(5, 6)
11
>>> jsonrpclib.__notify('add', (5, 6))

See http://code.google.com/p/jsonrpclib/ for more info.
"""

import types
import sys
from xmlrpclib import Transport as XMLTransport
from xmlrpclib import SafeTransport as XMLSafeTransport
from xmlrpclib import ServerProxy as XMLServerProxy
from xmlrpclib import _Method as XML_Method
import time

# JSON library importing
cjson = None
json = None
try:
    import cjson
except ImportError:
    pass
if not cjson:
    try:
        import json
    except ImportError:
        pass
if not cjson and not json: 
    try:
        import simplejson as json
    except ImportError:
        raise ImportError('You must have the cjson, json, or simplejson ' +
                          'module(s) available.')

# Library attributes
_version = 2.0
_last_response = None
_last_request = None
_user_agent = 'jsonrpclib/0.1 (Python %s)' % \
    '.'.join([str(ver) for ver in sys.version_info[0:3]])

#JSON Abstractions

def jdumps(obj, encoding='utf-8'):
    # Do 'serialize' test at some point for other classes
    global cjson
    if cjson:
        return cjson.encode(obj)
    else:
        return json.dumps(obj, encoding=encoding)

def jloads(json_string):
    global cjson
    if cjson:
        return cjson.decode(json_string)
    else:
        return json.loads(json_string)


# XMLRPClib re-implemntations

class ProtocolError(Exception):
    pass

class Transport(XMLTransport):
    """ Just extends the XMLRPC transport where necessary. """
    user_agent = _user_agent

    def send_content(self, connection, request_body):
        connection.putheader("Content-Type", "text/json")
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)

    def _parse_response(self, file_h, sock):
        response_body = ''
        while 1:
            if sock:
                response = sock.recv(1024)
            else:
                response = file_h.read(1024)
            if not response:
                break
            if self.verbose:
                print 'body: %s' % response
            response_body += response
        return_obj = loads(response_body)
        return return_obj

class SafeTransport(XMLSafeTransport):
    """ Just extends for HTTPS calls """
    user_agent = Transport.user_agent
    send_content = Transport.send_content
    _parse_response = Transport._parse_response

class ServerProxy(XMLServerProxy):
    """
    Unfortunately, much more of this class has to be copied since
    so much of it does the serialization.
    """

    def __init__(self, uri, transport=None, encoding=None, 
                 verbose=0, version=None):
        import urllib
        global _version
        if not version:
            version = _version
        self.__version = version
        schema, uri = urllib.splittype(uri)
        if schema not in ('http', 'https'):
            raise IOError('Unsupported JSON-RPC protocol.')
        self.__host, self.__handler = urllib.splithost(uri)
        if not self.__handler:
            # Not sure if this is in the JSON spec?
            self.__handler = '/RPC2'
        if transport is None:
            if schema == 'https':
                transport = SafeTransport()
            else:
                transport = Transport()
        self.__transport = transport
        self.__encoding = encoding
        self.__verbose = verbose

    def __request(self, methodname, params, rpcid=None):
        request = dumps(params, methodname, encoding=self.__encoding,
                        rpcid=rpcid, version=self.__version)
        response = self.__run_request(request)
        return response['result']
    
    def __notify(self, methodname, params, rpcid=None):
        request = dumps(params, methodname, encoding=self.__encoding,
                        rpcid=rpcid, version=self.__version, notify=True)
        response = self.__run_request(request, notify=True)
        return

    def __run_request(self, request, notify=None):
        global _last_request
        global _last_response
        _last_request = request
        
        if notify is True:
            _last_response = None
            return None

        response = self.__transport.request(
            self.__host,
            self.__handler,
            request,
            verbose=self.__verbose
        )
        
        # Here, the XMLRPC library translates a single list
        # response to the single value -- should we do the
        # same, and require a tuple / list to be passed to
        # the response object, or expect the Server to be 
        # outputting the response appropriately?
        
        _last_response = response
        return check_for_errors(response)

    def __getattr__(self, name):
        # Same as original, just with new _Method and wrapper 
        # for __notify
        if name in ('__notify', '__run_request'):
            wrapped_name = '_%s%s' % (self.__class__.__name__, name)
            return getattr(self, wrapped_name)
        return _Method(self.__request, name)

class _Method(XML_Method):
    def __call__(self, *args, **kwargs):
        if len(args) > 0 and len(kwargs) > 0:
            raise ProtocolError('Cannot use both positional ' +
                'and keyword arguments (according to JSON-RPC spec.)')
        if len(args) > 0:
            return self.__send(self.__name, args)
        else:
            return self.__send(self.__name, kwargs)

# Batch implementation

class Job(object):
    
    def __init__(self, method, notify=False):
        self.method = method
        self.params = []
        self.notify = notify

    def __call__(self, *args, **kwargs):
        if len(kwargs) > 0 and len(args) > 0:
            raise ProtocolError('A Job cannot have both positional ' +
                                'and keyword arguments.')
        if len(kwargs) > 0:
            self.params = kwargs
        else:
            self.params = args

    def request(self, encoding=None, rpcid=None):
        return dumps(self.params, self.method, version=2.0,
                     encoding=encoding, rpcid=rpcid, notify=self.notify)

    def __repr__(self):
        return '%s' % self.request()

class MultiCall(ServerProxy):
    
    def __init__(self, uri, *args, **kwargs):
        self.__job_list = []
        ServerProxy.__init__(self, uri, *args, **kwargs)

    def __run_request(self, request_body):
        run_request = getattr(ServerProxy, '_ServerProxy__run_request')
        return run_request(self, request_body)

    def __request(self):
        if len(self.__job_list) < 1:
            # Should we alert? This /is/ pretty obvious.
            return
        request_body = '[ %s ]' % ','.join([job.request() for
                                          job in self.__job_list])
        responses = self.__run_request(request_body)
        del self.__job_list[:]
        return [ response['result'] for response in responses ]

    def __notify(self, method, params):
        new_job = Job(method, notify=True)
        self.__job_list.append(new_job)

    def __getattr__(self, name):
        if name in ('__run', '__notify'):
            wrapped_name = '_%s%s' % (self.__class__.__name__, name)
            return getattr(self, wrapped_name)
        new_job = Job(name)
        self.__job_list.append(new_job)
        return new_job

    __call__ = __request

# These lines conform to xmlrpclib's "compatibility" line. 
# Not really sure if we should include these, but oh well.
Server = ServerProxy

class Fault(dict):
    # JSON-RPC error class
    def __init__(self, code=-32000, message='Server error'):
        self.faultCode = code
        self.faultString = message

    def error(self):
        return {'code':self.faultCode, 'message':self.faultString}

    def response(self, rpcid=None, version=None):
        global _version
        if not version:
            version = _version
        return dumps(self, rpcid=None, methodresponse=True,
                     version=version)

def random_id(length=8):
    import string
    import random
    random.seed()
    choices = string.lowercase+string.digits
    return_id = ''
    for i in range(length):
        return_id += random.choice(choices)
    return return_id

class Payload(dict):
    def __init__(self, rpcid=None, version=None):
        global _version
        if not version:
            version = _version
        self.id = rpcid
        self.version = float(version)
    
    def request(self, method, params=[]):
        if type(method) not in types.StringTypes:
            raise ValueError('Method name must be a string.')
        if not self.id:
            self.id = random_id()
        request = {'id':self.id, 'method':method, 'params':params}
        if self.version >= 2:
            request['jsonrpc'] = str(self.version)
        return request

    def notify(self, method, params=[]):
        request = self.request(method, params)
        if self.version >= 2:
            del request['id']
        else:
            request['id'] = None
        return request

    def response(self, result=None):
        response = {'result':result, 'id':self.id}
        if self.version >= 2:
            response['jsonrpc'] = str(self.version)
        else:
            response['error'] = None
        return response

    def error(self, code=-32000, message='Server error.'):
        error = self.response()
        if self.version >= 2:
            del error['result']
        else:
            error['result'] = None
        error['error'] = {'code':code, 'message':message}
        return error

def dumps(params=[], methodname=None, methodresponse=None, 
        encoding=None, rpcid=None, version=None, notify=None):
    """
    This differs from the Python implementation in that it implements 
    the rpcid argument since the 2.0 spec requires it for responses.
    """
    global _version
    if not version:
        verion = _version
    valid_params = (types.TupleType, types.ListType, types.DictType)
    if methodname in types.StringTypes and \
            type(params) not in valid_params and \
            not isinstance(params, Fault):
        """ 
        If a method, and params are not in a listish or a Fault,
        error out.
        """
        raise TypeError('Params must be a dict, list, tuple or Fault ' +
                        'instance.')
    if type(methodname) not in types.StringTypes and methodresponse != True:
        raise ValueError('Method name must be a string, or methodresponse '+
                         'must be set to True.')
    if isinstance(params, Fault) and not methodresponse:
        raise TypeError('You can only use a Fault for responses.')
    # Begin parsing object
    payload = Payload(rpcid=rpcid, version=version)
    if not encoding:
        encoding = 'utf-8'
    if type(params) is Fault:
        response = payload.error(params.faultCode, params.faultString)
        return jdumps(response, encoding=encoding)
    if methodresponse is True:
        if rpcid is None:
            raise ValueError('A method response must have an rpcid.')
        response = payload.response(params)
        return jdumps(response, encoding=encoding)
    request = None
    if notify == True:
        request = payload.notify(methodname, params)
    else:
        request = payload.request(methodname, params)
    return jdumps(request, encoding=encoding)

def loads(data):
    """
    This differs from the Python implementation, in that it returns
    the request structure in Dict format instead of the method, params.
    It will return a list in the case of a batch request / response.
    """
    result = jloads(data)
    # if the above raises an error, the implementing server code 
    # should return something like the following:
    # { 'jsonrpc':'2.0', 'error': fault.error(), id: None }
    return result

def check_for_errors(result):
    result_list = []
    if not isbatch(result):
        result_list.append(result)
    else:
        result_list = result
    for entry in result_list:
        if 'jsonrpc' in entry.keys() and float(entry['jsonrpc']) > 2.0:
            raise NotImplementedError('JSON-RPC version not yet supported.')
        if 'error' in entry.keys() and entry['error'] != None:
            code = entry['error']['code']
            message = entry['error']['message']
            raise ProtocolError('ERROR %s: %s' % (code, message))
    del result_list
    return result

def isbatch(result):
    if type(result) not in (types.ListType, types.TupleType):
        return False
    if len(result) < 1:
        return False
    if type(result[0]) is not types.DictType:
        return False
    if 'jsonrpc' not in result[0].keys():
        return False
    try:
        version = float(result[0]['jsonrpc'])
    except ValueError:
        raise ProtocolError('"jsonrpc" key must be a float(able) value.')
    if version < 2:
        return False
    return True



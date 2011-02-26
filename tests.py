"""
The tests in this file compare the request and response objects
to the JSON-RPC 2.0 specification document, as well as testing
several internal components of the jsonrpclib library. Run this 
module without any parameters to run the tests.

Currently, this is not easily tested with a framework like 
nosetests because we spin up a daemon thread running the
the Server, and nosetests (at least in my tests) does not
ever "kill" the thread.

If you are testing jsonrpclib and the module doesn't return to
the command prompt after running the tests, you can hit 
"Ctrl-C" (or "Ctrl-Break" on Windows) and that should kill it.

TODO:
* Finish implementing JSON-RPC 2.0 Spec tests
* Implement JSON-RPC 1.0 tests
* Implement JSONClass, History, Config tests
"""

from jsonrpclib import Server, MultiCall, history, config, ProtocolError
from jsonrpclib import jsonrpc
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCRequestHandler
import socket
import tempfile
import unittest
import os
import time
try:
    import json
except ImportError:
    import simplejson as json
from threading import Thread

PORTS = range(8000, 8999)

class TestCompatibility(unittest.TestCase):
    
    client = None
    port = None
    server = None
    
    def setUp(self):
        self.port = PORTS.pop()
        self.server = server_set_up(addr=('', self.port))
        self.client = Server('http://localhost:%d' % self.port)
    
    # v1 tests forthcoming
    
    # Version 2.0 Tests
    def test_positional(self):
        """ Positional arguments in a single call """
        result = self.client.subtract(23, 42)
        self.assertTrue(result == -19)
        result = self.client.subtract(42, 23)
        self.assertTrue(result == 19)
        request = json.loads(history.request)
        response = json.loads(history.response)
        verify_request = {
            "jsonrpc": "2.0", "method": "subtract", 
            "params": [42, 23], "id": request['id']
        }
        verify_response = {
            "jsonrpc": "2.0", "result": 19, "id": request['id']
        }
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)
        
    def test_named(self):
        """ Named arguments in a single call """
        result = self.client.subtract(subtrahend=23, minuend=42)
        self.assertTrue(result == 19)
        result = self.client.subtract(minuend=42, subtrahend=23)
        self.assertTrue(result == 19)
        request = json.loads(history.request)
        response = json.loads(history.response)
        verify_request = {
            "jsonrpc": "2.0", "method": "subtract", 
            "params": {"subtrahend": 23, "minuend": 42}, 
            "id": request['id']
        }
        verify_response = {
            "jsonrpc": "2.0", "result": 19, "id": request['id']
        }
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)
        
    def test_notification(self):
        """ Testing a notification (response should be null) """
        result = self.client._notify.update(1, 2, 3, 4, 5)
        self.assertTrue(result == None)
        request = json.loads(history.request)
        response = history.response
        verify_request = {
            "jsonrpc": "2.0", "method": "update", "params": [1,2,3,4,5]
        }
        verify_response = ''
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)
        
    def test_non_existent_method(self):
        self.assertRaises(ProtocolError, self.client.foobar)
        request = json.loads(history.request)
        response = json.loads(history.response)
        verify_request = {
            "jsonrpc": "2.0", "method": "foobar", "id": request['id']
        }
        verify_response = {
            "jsonrpc": "2.0", 
            "error": 
                {"code": -32601, "message": response['error']['message']}, 
            "id": request['id']
        }
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)
        
    def test_invalid_json(self):
        invalid_json = '{"jsonrpc": "2.0", "method": "foobar, '+ \
            '"params": "bar", "baz]'
        response = self.client._run_request(invalid_json)
        response = json.loads(history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32700,'+
            ' "message": "Parse error."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)
        
    def test_invalid_request(self):
        invalid_request = '{"jsonrpc": "2.0", "method": 1, "params": "bar"}'
        response = self.client._run_request(invalid_request)
        response = json.loads(history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32600, '+
            '"message": "Invalid Request."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)
        
    def test_batch_invalid_json(self):
        invalid_request = '[ {"jsonrpc": "2.0", "method": "sum", '+ \
            '"params": [1,2,4], "id": "1"},{"jsonrpc": "2.0", "method" ]'
        response = self.client._run_request(invalid_request)
        response = json.loads(history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32700,'+
            '"message": "Parse error."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)
        
    def test_empty_array(self):
        invalid_request = '[]'
        response = self.client._run_request(invalid_request)
        response = json.loads(history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32600, '+
            '"message": "Invalid Request."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)
        
    def test_nonempty_array(self):
        invalid_request = '[1,2]'
        request_obj = json.loads(invalid_request)
        response = self.client._run_request(invalid_request)
        response = json.loads(history.response)
        self.assertTrue(len(response) == len(request_obj))
        for resp in response:
            verify_resp = json.loads(
                '{"jsonrpc": "2.0", "error": {"code": -32600, '+
                '"message": "Invalid Request."}, "id": null}'
            )
            verify_resp['error']['message'] = resp['error']['message']
            self.assertTrue(resp == verify_resp)
        
    def test_batch(self):
        multicall = MultiCall(self.client)
        multicall.sum(1,2,4)
        multicall._notify.notify_hello(7)
        multicall.subtract(42,23)
        multicall.foo.get(name='myself')
        multicall.get_data()
        job_requests = [j.request() for j in multicall._job_list]
        job_requests.insert(3, '{"foo": "boo"}')
        json_requests = '[%s]' % ','.join(job_requests)
        requests = json.loads(json_requests)
        responses = self.client._run_request(json_requests)
        
        verify_requests = json.loads("""[
            {"jsonrpc": "2.0", "method": "sum", "params": [1,2,4], "id": "1"},
            {"jsonrpc": "2.0", "method": "notify_hello", "params": [7]},
            {"jsonrpc": "2.0", "method": "subtract", "params": [42,23], "id": "2"},
            {"foo": "boo"},
            {"jsonrpc": "2.0", "method": "foo.get", "params": {"name": "myself"}, "id": "5"},
            {"jsonrpc": "2.0", "method": "get_data", "id": "9"} 
        ]""")
            
        # Thankfully, these are in order so testing is pretty simple.
        verify_responses = json.loads("""[
            {"jsonrpc": "2.0", "result": 7, "id": "1"},
            {"jsonrpc": "2.0", "result": 19, "id": "2"},
            {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request."}, "id": null},
            {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found."}, "id": "5"},
            {"jsonrpc": "2.0", "result": ["hello", 5], "id": "9"}
        ]""")
        
        self.assertTrue(len(requests) == len(verify_requests))
        self.assertTrue(len(responses) == len(verify_responses))
        
        responses_by_id = {}
        response_i = 0
        
        for i in range(len(requests)):
            verify_request = verify_requests[i]
            request = requests[i]
            response = None
            if request.get('method') != 'notify_hello':
                req_id = request.get('id')
                if verify_request.has_key('id'):
                    verify_request['id'] = req_id
                verify_response = verify_responses[response_i]
                verify_response['id'] = req_id
                responses_by_id[req_id] = verify_response
                response_i += 1
                response = verify_response
            self.assertTrue(request == verify_request)
            
        for response in responses:
            verify_response = responses_by_id.get(response.get('id'))
            if verify_response.has_key('error'):
                verify_response['error']['message'] = \
                    response['error']['message']
            self.assertTrue(response == verify_response)
        
    def test_batch_notifications(self):    
        multicall = MultiCall(self.client)
        multicall._notify.notify_sum(1, 2, 4)
        multicall._notify.notify_hello(7)
        result = multicall()
        self.assertTrue(len(result) == 0)
        valid_request = json.loads(
            '[{"jsonrpc": "2.0", "method": "notify_sum", '+
            '"params": [1,2,4]},{"jsonrpc": "2.0", '+
            '"method": "notify_hello", "params": [7]}]'
        )
        request = json.loads(history.request)
        self.assertTrue(len(request) == len(valid_request))
        for i in range(len(request)):
            req = request[i]
            valid_req = valid_request[i]
            self.assertTrue(req == valid_req)
        self.assertTrue(history.response == '')
        
class InternalTests(unittest.TestCase):
    """ 
    These tests verify that the client and server portions of 
    jsonrpclib talk to each other properly.
    """    
    client = None
    server = None
    port = None
    
    def setUp(self):
        self.port = PORTS.pop()
        self.server = server_set_up(addr=('', self.port))
    
    def get_client(self):
        return Server('http://localhost:%d' % self.port)
        
    def get_multicall_client(self):
        server = self.get_client()
        return MultiCall(server)

    def test_connect(self):
        client = self.get_client()
        result = client.ping()
        self.assertTrue(result)
        
    def test_single_args(self):
        client = self.get_client()
        result = client.add(5, 10)
        self.assertTrue(result == 15)
        
    def test_single_kwargs(self):
        client = self.get_client()
        result = client.add(x=5, y=10)
        self.assertTrue(result == 15)
        
    def test_single_kwargs_and_args(self):
        client = self.get_client()
        self.assertRaises(ProtocolError, client.add, (5,), {'y':10})
        
    def test_single_notify(self):
        client = self.get_client()
        result = client._notify.add(5, 10)
        self.assertTrue(result == None)
    
    def test_single_namespace(self):
        client = self.get_client()
        response = client.namespace.sum(1,2,4)
        request = json.loads(history.request)
        response = json.loads(history.response)
        verify_request = {
            "jsonrpc": "2.0", "params": [1, 2, 4], 
            "id": "5", "method": "namespace.sum"
        }
        verify_response = {
            "jsonrpc": "2.0", "result": 7, "id": "5"
        }
        verify_request['id'] = request['id']
        verify_response['id'] = request['id']
        self.assertTrue(verify_request == request)
        self.assertTrue(verify_response == response)
        
    def test_multicall_success(self):
        multicall = self.get_multicall_client()
        multicall.ping()
        multicall.add(5, 10)
        multicall.namespace.sum([5, 10, 15])
        correct = [True, 15, 30]
        i = 0
        for result in multicall():
            self.assertTrue(result == correct[i])
            i += 1
            
    def test_multicall_success(self):
        multicall = self.get_multicall_client()
        for i in range(3):
            multicall.add(5, i)
        result = multicall()
        self.assertTrue(result[2] == 7)
    
    def test_multicall_failure(self):
        multicall = self.get_multicall_client()
        multicall.ping()
        multicall.add(x=5, y=10, z=10)
        raises = [None, ProtocolError]
        result = multicall()
        for i in range(2):
            if not raises[i]:
                result[i]
            else:
                def func():
                    return result[i]
                self.assertRaises(raises[i], func)
        
        
if jsonrpc.USE_UNIX_SOCKETS:
    # We won't do these tests unless Unix Sockets are supported
    
    class UnixSocketInternalTests(InternalTests):
        """
        These tests run the same internal communication tests, 
        but over a Unix socket instead of a TCP socket.
        """
        def setUp(self):
            suffix = "%d.sock" % PORTS.pop()
            
            # Open to safer, alternative processes 
            # for getting a temp file name...
            temp = tempfile.NamedTemporaryFile(
                suffix=suffix
            )
            self.port = temp.name
            temp.close()
            
            self.server = server_set_up(
                addr=self.port, 
                address_family=socket.AF_UNIX
            )

        def get_client(self):
            return Server('unix:/%s' % self.port)
            
        def tearDown(self):
            """ Removes the tempory socket file """
            os.unlink(self.port)
            
class UnixSocketErrorTests(unittest.TestCase):
    """ 
    Simply tests that the proper exceptions fire if 
    Unix sockets are attempted to be used on a platform
    that doesn't support them.
    """
    
    def setUp(self):
        self.original_value = jsonrpc.USE_UNIX_SOCKETS
        if (jsonrpc.USE_UNIX_SOCKETS):
            jsonrpc.USE_UNIX_SOCKETS = False
        
    def test_client(self):
        address = "unix://shouldnt/work.sock"
        self.assertRaises(
            jsonrpc.UnixSocketMissing,
            Server,
            address
        )
        
    def tearDown(self):
        jsonrpc.USE_UNIX_SOCKETS = self.original_value
        

""" Test Methods """
def subtract(minuend, subtrahend):
    """ Using the keywords from the JSON-RPC v2 doc """
    return minuend-subtrahend
    
def add(x, y):
    return x + y
    
def update(*args):
    return args
    
def summation(*args):
    return sum(args)
    
def notify_hello(*args):
    return args
    
def get_data():
    return ['hello', 5]
        
def ping():
    return True
        
def server_set_up(addr, address_family=socket.AF_INET):
    # Not sure this is a good idea to spin up a new server thread
    # for each test... but it seems to work fine.
    def log_request(self, *args, **kwargs):
        """ Making the server output 'quiet' """
        pass
    SimpleJSONRPCRequestHandler.log_request = log_request
    server = SimpleJSONRPCServer(addr, address_family=address_family)
    server.register_function(summation, 'sum')
    server.register_function(summation, 'notify_sum')
    server.register_function(notify_hello)
    server.register_function(subtract)
    server.register_function(update)
    server.register_function(get_data)
    server.register_function(add)
    server.register_function(ping)
    server.register_function(summation, 'namespace.sum')
    server_proc = Thread(target=server.serve_forever)
    server_proc.daemon = True
    server_proc.start()
    return server_proc

if __name__ == '__main__':
    print "==============================================================="
    print "  NOTE: There may be threading exceptions after tests finish.  "
    print "==============================================================="
    time.sleep(2)
    unittest.main()

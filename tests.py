#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
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


Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

:license: Apache License 2.0
:version: 1.0.0
"""

# Module version
__version_info__ = (1, 0, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# jsonrpclib
from jsonrpclib import Server, MultiCall, ProtocolError
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer, WSGIJSONRPCApp
from jsonrpclib.utils import from_bytes
import jsonrpclib.history

# Standard library
import contextlib
import re
import sys
import threading
import time
import unittest
import wsgiref.validate
import wsgiref.simple_server

try:
    # Python 2
    from StringIO import StringIO

except ImportError:
    # Python 3
    from io import StringIO

try:
    import json

except ImportError:
    import simplejson as json

# ------------------------------------------------------------------------------

PORTS = list(range(8000, 8999))

# ------------------------------------------------------------------------------
# Test methods

def subtract(minuend, subtrahend):
    """
    Using the keywords from the JSON-RPC v2 doc
    """
    return minuend - subtrahend

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

@staticmethod
def TCPJSONRPCServer(addr, port):
    return SimpleJSONRPCServer((addr, port), logRequests=False)

@staticmethod
def WSGIJSONRPCServer(addr, port):
    class NoLogHandler(wsgiref.simple_server.WSGIRequestHandler):
        def log_message(self, format, *args):
            pass

    return wsgiref.simple_server.make_server(addr, port, WSGIJSONRPCApp(),
         handler_class=NoLogHandler)

# ------------------------------------------------------------------------------
# Server utility class

class UtilityServer(object):
    """
    Utility start/stop server
    """
    def __init__(self):
        """
        Sets up members
        """
        self._server = None
        self._thread = None


    def start(self, server_cls, addr, port):
        """
        Starts the server

        :param server_cls: Callable that returns a subclass of XMLRPCServer
        :param addr: A binding address
        :param port: A listening port
        :return: This object (for in-line calls)
        """
        # Create the server
        self._server = server = server_cls(addr, port)
        if hasattr(server, 'get_app'):
            server = server.get_app()

        # Register test methods
        server.register_function(summation, 'sum')
        server.register_function(summation, 'notify_sum')
        server.register_function(notify_hello)
        server.register_function(subtract)
        server.register_function(update)
        server.register_function(get_data)
        server.register_function(add)
        server.register_function(ping)
        server.register_function(summation, 'namespace.sum')

        # Serve in a thread
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()

        # Allow an in-line instantiation
        return self


    def stop(self):
        """
        Stops the server and waits for its thread to finish
        """
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()

        self._server = None
        self._thread = None

# ------------------------------------------------------------------------------

class TestCompatibility(unittest.TestCase):

    client = None
    port = None
    server = None
    server_cls = TCPJSONRPCServer

    def setUp(self):
        """
        Pre-test set up
        """
        # Set up the server
        self.port = PORTS.pop()
        self.server = UtilityServer().start(self.server_cls, '', self.port)

        # Set up the client
        self.history = jsonrpclib.history.History()
        self.client = Server('http://localhost:{0}'.format(self.port),
                             history=self.history)


    def tearDown(self):
        """
        Post-test clean up
        """
        # Close the client
        self.client("close")()

        # Stop the server
        self.server.stop()


    # v1 tests forthcoming

    # Version 2.0 Tests
    def test_positional(self):
        """ Positional arguments in a single call """
        result = self.client.subtract(23, 42)
        self.assertTrue(result == -19)
        result = self.client.subtract(42, 23)
        self.assertTrue(result == 19)
        request = json.loads(self.history.request)
        response = json.loads(self.history.response)
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
        request = json.loads(self.history.request)
        response = json.loads(self.history.response)
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
        request = json.loads(self.history.request)
        response = self.history.response
        verify_request = {
            "jsonrpc": "2.0", "method": "update", "params": [1, 2, 3, 4, 5]
        }
        verify_response = ''
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)

    def test_non_existent_method(self):
        self.assertRaises(ProtocolError, self.client.foobar)
        request = json.loads(self.history.request)
        response = json.loads(self.history.response)
        verify_request = {
            "jsonrpc": "2.0", "method": "foobar", "id": request['id']
        }
        verify_response = {
            "jsonrpc": "2.0",
            "error":
                {"code":-32601, "message": response['error']['message']},
            "id": request['id']
        }
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)

    def test_invalid_json(self):
        invalid_json = '{"jsonrpc": "2.0", "method": "foobar, ' + \
            '"params": "bar", "baz]'
        self.client._run_request(invalid_json)
        response = json.loads(self.history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32700,' +
            ' "message": "Parse error."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)

    def test_invalid_request(self):
        invalid_request = '{"jsonrpc": "2.0", "method": 1, "params": "bar"}'
        self.client._run_request(invalid_request)
        response = json.loads(self.history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32600, ' +
            '"message": "Invalid Request."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)

    def test_batch_invalid_json(self):
        invalid_request = '[ {"jsonrpc": "2.0", "method": "sum", ' + \
            '"params": [1,2,4], "id": "1"},{"jsonrpc": "2.0", "method" ]'
        self.client._run_request(invalid_request)
        response = json.loads(self.history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32700,' +
            '"message": "Parse error."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)

    def test_empty_array(self):
        invalid_request = '[]'
        self.client._run_request(invalid_request)
        response = json.loads(self.history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32600, ' +
            '"message": "Invalid Request."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)

    def test_nonempty_array(self):
        invalid_request = '[1,2]'
        request_obj = json.loads(invalid_request)
        self.client._run_request(invalid_request)
        response = json.loads(self.history.response)
        self.assertTrue(len(response) == len(request_obj))
        for resp in response:
            verify_resp = json.loads(
                '{"jsonrpc": "2.0", "error": {"code": -32600, ' +
                '"message": "Invalid Request."}, "id": null}'
            )
            verify_resp['error']['message'] = resp['error']['message']
            self.assertTrue(resp == verify_resp)

    def test_batch(self):
        multicall = MultiCall(self.client)
        multicall.sum(1, 2, 4)
        multicall._notify.notify_hello(7)
        multicall.subtract(42, 23)
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
                if 'id' in verify_request:
                    verify_request['id'] = req_id
                verify_response = verify_responses[response_i]
                verify_response['id'] = req_id
                responses_by_id[req_id] = verify_response
                response_i += 1
                response = verify_response
            self.assertTrue(request == verify_request)

        for response in responses:
            verify_response = responses_by_id.get(response.get('id'))
            if 'error' in verify_response:
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
            '[{"jsonrpc": "2.0", "method": "notify_sum", ' +
            '"params": [1,2,4]},{"jsonrpc": "2.0", ' +
            '"method": "notify_hello", "params": [7]}]'
        )
        request = json.loads(self.history.request)
        self.assertTrue(len(request) == len(valid_request))
        for i in range(len(request)):
            req = request[i]
            valid_req = valid_request[i]
            self.assertTrue(req == valid_req)
        self.assertTrue(self.history.response == '')

# ------------------------------------------------------------------------------

class WSGITestCompatibility(TestCompatibility):
    server_cls = WSGIJSONRPCServer

# ------------------------------------------------------------------------------

class InternalTests(unittest.TestCase):
    """
    These tests verify that the client and server portions of
    jsonrpclib talk to each other properly.
    """
    server = None
    port = None
    server_cls = TCPJSONRPCServer

    def setUp(self):
        # Set up the server
        self.port = PORTS.pop()
        self.server = UtilityServer().start(self.server_cls, '', self.port)

        # Prepare the client
        self.history = jsonrpclib.history.History()


    def tearDown(self):
        """
        Post-test clean up
        """
        # Stop the server
        self.server.stop()


    def get_client(self):
        return Server('http://localhost:{0}'.format(self.port),
                      history=self.history)

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
        client.namespace.sum(1, 2, 4)
        request = json.loads(self.history.request)
        response = json.loads(self.history.response)
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
        multicall.namespace.sum(5, 10, 15)
        correct = [True, 15, 30]

        for i, result in enumerate(multicall()):
            self.assertTrue(result == correct[i])

    def test_multicall_success_2(self):
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

# ------------------------------------------------------------------------------

class WSGIInternalTests(InternalTests):
    server_cls = WSGIJSONRPCServer

# ------------------------------------------------------------------------------

class HeadersTests(unittest.TestCase):
    """
    These tests verify functionality of additional headers.
    """
    server = None
    port = None
    server_cls = TCPJSONRPCServer

    REQUEST_LINE = "^send: POST"

    def setUp(self):
        """
        Sets up the test
        """
        # Set up the server
        self.port = PORTS.pop()
        self.server = UtilityServer().start(self.server_cls, '', self.port)


    def tearDown(self):
        """
        Post-test clean up
        """
        # Stop the server
        self.server.stop()


    @contextlib.contextmanager
    def captured_headers(self):
        """
        Captures the request headers. Yields the {header : value} dictionary,
        where keys are in lower case.
        """
        # Redirect the standard output, to catch jsonrpclib verbose messages
        stdout = sys.stdout
        sys.stdout = f = StringIO()
        headers = {}
        yield headers
        sys.stdout = stdout

        # Extract the sent request content
        request_lines = f.getvalue().splitlines()
        request_lines = list(filter(lambda l: l.startswith("send:"),
                                    request_lines))
        request_line = request_lines[0].split("send: ") [-1]

        # Convert it to a string
        try:
            # Use eval to convert the representation into a string
            request_line = from_bytes(eval(request_line))
        except:
            # Keep the received version
            pass

        # Extract headers
        raw_headers = request_line.splitlines()[1:-1]
        raw_headers = map(lambda h: re.split(":\s?", h, 1), raw_headers)
        for header, value in raw_headers:
            headers[header.lower()] = value


    def test_should_extract_headers(self):
        # given
        client = Server('http://localhost:{0}'.format(self.port), verbose=1)

        # when
        with self.captured_headers() as headers:
            response = client.ping()
            self.assertTrue(response)

        # then
        self.assertTrue(len(headers) > 0)
        self.assertTrue('content-type' in headers)
        self.assertEqual(headers['content-type'], 'application/json-rpc')

    def test_should_add_additional_headers(self):
        # given
        client = Server('http://localhost:{0}'.format(self.port), verbose=1,
                        headers={'X-My-Header' : 'Test'})

        # when
        with self.captured_headers() as headers:
            response = client.ping()
            self.assertTrue(response)

        # then
        self.assertTrue('x-my-header' in headers)
        self.assertEqual(headers['x-my-header'], 'Test')

    def test_should_add_additional_headers_to_notifications(self):
        # given
        client = Server('http://localhost:{0}'.format(self.port), verbose=1,
                        headers={'X-My-Header' : 'Test'})

        # when
        with self.captured_headers() as headers:
            client._notify.ping()

        # then
        self.assertTrue('x-my-header' in headers)
        self.assertEqual(headers['x-my-header'], 'Test')

    def test_should_override_headers(self):
        # given
        client = Server('http://localhost:{0}'.format(self.port), verbose=1,
                        headers={
                                 'User-Agent' : 'jsonrpclib test',
                                 'Host' : 'example.com'
                                 })

        # when
        with self.captured_headers() as headers:
            response = client.ping()
            self.assertTrue(response)

        # then
        self.assertEqual(headers['user-agent'], 'jsonrpclib test')
        self.assertEqual(headers['host'], 'example.com')

    def test_should_not_override_content_length(self):
        # given
        client = Server('http://localhost:{0}'.format(self.port), verbose=1,
                        headers={'Content-Length' : 'invalid value'})

        # when
        with self.captured_headers() as headers:
            response = client.ping()
            self.assertTrue(response)

        # then
        self.assertTrue('content-length' in headers)
        self.assertNotEqual(headers['content-length'], 'invalid value')

    def test_should_convert_header_values_to_basestring(self):
        # given
        client = Server('http://localhost:{0}'.format(self.port), verbose=1,
                        headers={'X-Test' : 123})

        # when
        with self.captured_headers() as headers:
            response = client.ping()
            self.assertTrue(response)

        # then
        self.assertTrue('x-test' in headers)
        self.assertEqual(headers['x-test'], '123')

    def test_should_add_custom_headers_to_methods(self):
        # given
        client = Server('http://localhost:{0}'.format(self.port), verbose=1)

        # when
        with self.captured_headers() as headers:
            with client._additional_headers({'X-Method' : 'Method'}) as cl:
                response = cl.ping()

            self.assertTrue(response)

        # then
        self.assertTrue('x-method' in headers)
        self.assertEqual(headers['x-method'], 'Method')

    def test_should_override_global_headers(self):
        # given
        client = Server('http://localhost:{0}'.format(self.port), verbose=1,
                        headers={'X-Test' : 'Global'})

        # when
        with self.captured_headers() as headers:
            with client._additional_headers({'X-Test' : 'Method'}) as cl:
                response = cl.ping()
                self.assertTrue(response)

        # then
        self.assertTrue('x-test' in headers)
        self.assertEqual(headers['x-test'], 'Method')

    def test_should_restore_global_headers(self):
        # given
        client = Server('http://localhost:{0}'.format(self.port), verbose=1,
                        headers={'X-Test' : 'Global'})

        # when
        with self.captured_headers() as headers:
            with client._additional_headers({'X-Test' : 'Method'}) as cl:
                response = cl.ping()
                self.assertTrue(response)

        self.assertTrue('x-test' in headers)
        self.assertEqual(headers['x-test'], 'Method')

        with self.captured_headers() as headers:
            response = cl.ping()
            self.assertTrue(response)

        # then
        self.assertTrue('x-test' in headers)
        self.assertEqual(headers['x-test'], 'Global')


    def test_should_allow_to_nest_additional_header_blocks(self):
        # given
        client = Server('http://localhost:%d' % self.port, verbose=1)

        # when
        with client._additional_headers({'X-Level-1' : '1'}) as cl_level1:
            with self.captured_headers() as headers1:
                response = cl_level1.ping()
                self.assertTrue(response)

            with cl_level1._additional_headers({'X-Level-2' : '2'}) as cl:
                with self.captured_headers() as headers2:
                    response = cl.ping()
                    self.assertTrue(response)

        # then
        self.assertTrue('x-level-1' in headers1)
        self.assertEqual(headers1['x-level-1'], '1')

        self.assertTrue('x-level-1' in headers2)
        self.assertEqual(headers1['x-level-1'], '1')
        self.assertTrue('x-level-2' in headers2)
        self.assertEqual(headers2['x-level-2'], '2')

# ------------------------------------------------------------------------------

class WSGIHeadersTests(HeadersTests):
    server_cls = WSGIJSONRPCServer

# ------------------------------------------------------------------------------

if __name__ == '__main__':
    print("===============================================================")
    print("  NOTE: There may be threading exceptions after tests finish.  ")
    print("===============================================================")
    time.sleep(.5)
    unittest.main()

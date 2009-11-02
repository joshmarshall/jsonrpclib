
class History(object):
    """
    This holds all the response and request objects for a
    session. A server using this should call "clear" after
    each request cycle in order to keep it from clogging 
    memory.
    """
    requests = []
    responses = []

    def add_response(self, response_obj):
        self.responses.append(response_obj)
    
    def add_request(self, request_obj):
        self.requests.append(request_obj)

    @property
    def request(self):
        if len(self.requests) == 0:
            return None
        else:
            return self.requests[-1]

    @property
    def response(self):
        if len(self.responses) == 0:
            return None
        else:
            return self.responses[-1]

    def clear(self):
        del self.requests[:]
        del self.responses[:]

history = History()

#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
The history module.
"""

__version__ = "0.1.5"

# ------------------------------------------------------------------------------

class History(object):
    """
    This holds all the response and request objects for a
    session. A server using this should call "clear" after
    each request cycle in order to keep it from clogging 
    memory.
    """
    def __init__(self):
        """
        Sets up members
        """
        self.requests = []
        self.responses = []

    def add_response(self, response_obj):
        """
        Adds a response to the history
        
        :param response_obj: Response content
        """
        self.responses.append(response_obj)

    def add_request(self, request_obj):
        """
        Adds a request to the history
        
        :param request_obj: A request object
        """
        self.requests.append(request_obj)

    @property
    def request(self):
        """
        Returns the latest stored request or None
        
        :return: The latest stored request
        """
        try:
            return self.requests[-1]

        except IndexError:
            return None

    @property
    def response(self):
        """
        Returns the latest stored response or None
        
        :return: The latest stored response
        """
        try:
            return self.responses[-1]

        except IndexError:
            return None


    def clear(self):
        """
        Clears the history lists
        """
        del self.requests[:]
        del self.responses[:]

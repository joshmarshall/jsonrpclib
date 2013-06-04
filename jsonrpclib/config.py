#!/usr/bin/python
# -- Content-Encoding: UTF-8 --

import sys

class LocalClasses(dict):
    def add(self, cls):
        self[cls.__name__] = cls

class Config(object):
    """
    This is pretty much used exclusively for the 'jsonclass' 
    functionality... set use_jsonclass to False to turn it off.
    You can change serialize_method and ignore_attribute, or use
    the local_classes.add(class) to include "local" classes.
    """
    # Change to False to keep __jsonclass__ entries raw.
    use_jsonclass = True

    # The serialize_method should be a string that references the
    # method on a custom class object which is responsible for
    # returning a tuple of the constructor arguments and a dict of
    # attributes.
    serialize_method = '_serialize'

    # The ignore attribute should be a string that references the
    # attribute on a custom class object which holds strings and / or
    # references of the attributes the class translator should ignore.
    ignore_attribute = '_ignore'

    # The list of classes to use for jsonclass translation.
    classes = LocalClasses()

    # Version of the JSON-RPC spec to support
    version = 2.0

    # User agent to use for calls.
    user_agent = 'jsonrpclib-pelix/0.1 (Python {0})' \
                 .format('.'.join(str(ver) for ver in sys.version_info[0:3]))

    # "Singleton" of Config
    _instance = None

    @classmethod
    def instance(cls):
        """
        Returns/Creates the instance of Config
        """
        if not cls._instance:
            cls._instance = cls()

        return cls._instance

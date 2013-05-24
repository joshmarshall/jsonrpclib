#!/usr/bin/python
# -- Content-Encoding: UTF-8 --

# Create a configuration instance
from jsonrpclib.config import Config
config = Config.instance()

# Create a history instance
from jsonrpclib.history import History
history = History.instance()

# Easy access to utility methods
from jsonrpclib.jsonrpc import Server, MultiCall, Fault, ProtocolError
from jsonrpclib.jsonrpc import loads, dumps, load, dump
from jsonrpclib.jsonrpc import jloads, jdumps
import jsonrpclib.utils as utils

#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Aliases to ease access to jsonrpclib classes

:license: Apache License 2.0
"""

# Easy access to utility methods and classes
from jsonrpclib.jsonrpc import Server, ServerProxy
from jsonrpclib.jsonrpc import MultiCall, Fault, ProtocolError, AppError
from jsonrpclib.jsonrpc import loads, dumps, load, dump
from jsonrpclib.jsonrpc import jloads, jdumps
import jsonrpclib.utils as utils

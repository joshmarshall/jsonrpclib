from jsonrpclib.config import Config
from jsonrpclib.history import History
from jsonrpclib.jsonrpc import Server, MultiCall, Fault
from jsonrpclib.jsonrpc import ProtocolError, loads, dumps

config = Config.instance()
history = History.instance()

__all__ = [
    "config", "Config", "history", "History", "Server", "MultiCall",
    "Fault", "ProtocolError", "loads", "dumps"
]

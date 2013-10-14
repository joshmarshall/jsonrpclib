#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Utility methods, for compatibility between Python version

:author: Thomas Calmant
:version: 1.0.1
"""

__version__ = "1.0.1"

# ------------------------------------------------------------------------------

import sys

# ------------------------------------------------------------------------------

if sys.version_info[0] < 3:
    # Python 2
    import types
    StringTypes = types.StringTypes

    string_types = (
        types.StringType,
        types.UnicodeType
    )

    numeric_types = (
        types.IntType,
        types.LongType,
        types.FloatType
    )

    def to_bytes(string):
        """
        Converts the given string into bytes
        """
        if type(string) is unicode:
            return str(string)

        return string

    def from_bytes(data):
        """
        Converts the given bytes into a string
        """
        if type(data) is str:
            return data

        return str(data)

# ------------------------------------------------------------------------------

else:
    # Python 3
    StringTypes = (str,)

    string_types = (
        bytes,
        str
    )

    numeric_types = (
        int,
        float
    )

    def to_bytes(string):
        """
        Converts the given string into bytes
        """
        if type(string) is bytes:
            return string

        return bytes(string, "UTF-8")

    def from_bytes(data):
        """
        Converts the given bytes into a string
        """
        if type(data) is str:
            return data

        return str(data, "UTF-8")

# ------------------------------------------------------------------------------
# Common

DictType = dict
ListType = list
SetTypes = (set, frozenset)
TupleType = tuple

iter_types = (
    dict,
    list,
    set, frozenset,
    tuple
)

value_types = (
    bool,
    type(None)
)

primitive_types = string_types + numeric_types + value_types

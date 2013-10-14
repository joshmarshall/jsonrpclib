#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Utility methods, for compatibility between Python version

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

:author: Thomas Calmant
:license: Apache License 2.0
:version: 1.0.1
"""

# Module version
__version_info__ = (1, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

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

iterable_types = (
    list,
    set, frozenset,
    tuple
)

value_types = (
    bool,
    type(None)
)

primitive_types = string_types + numeric_types + value_types

#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
The serialization module

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
:version: 0.1.6
"""

# Module version
__version_info__ = (0, 1, 6)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Local package
import jsonrpclib.config
import jsonrpclib.utils as utils

# Standard library
import inspect
import re

# ------------------------------------------------------------------------------

# Supported transmitted code
supported_types = (utils.DictType,) + utils.iterable_types \
                  + utils.primitive_types

# Regex of invalid module characters
invalid_module_chars = r'[^a-zA-Z0-9\_\.]'

# ------------------------------------------------------------------------------

class TranslationError(Exception):
    """
    Unmarshaling exception
    """
    pass

# ------------------------------------------------------------------------------

def dump(obj, serialize_method=None, ignore_attribute=None, ignore=[],
         config=jsonrpclib.config.DEFAULT):
    """
    Transforms the given object into a JSON-RPC compliant form.
    Converts beans into dictionaries with a __jsonclass__ entry.
    Doesn't change primitive types.

    :param obj: An object to convert
    :param serialize_method: Custom serialization method
    :param ignore_attribute: Name of the object attribute containing the names
                             of members to ignore
    :param ignore: A list of members to ignore
    :param config: A JSONRPClib Config instance
    :return: A JSON-RPC compliant object
    """
    if not serialize_method:
        serialize_method = config.serialize_method

    if not ignore_attribute:
        ignore_attribute = config.ignore_attribute

    # Parse / return default "types"...
    # Primitive
    if isinstance(obj, utils.primitive_types):
        return obj

    # Iterative
    elif isinstance(obj, utils.iterable_types):
        # List, set or tuple
        return [dump(item, serialize_method, ignore_attribute, ignore)
                for item in obj]

    elif isinstance(obj, utils.DictType):
        # Dictionary
        return dict((key, dump(value, serialize_method,
                               ignore_attribute, ignore))
                    for key, value in obj.items())

    # It's not a standard type, so it needs __jsonclass__
    module_name = inspect.getmodule(obj).__name__
    json_class = obj.__class__.__name__

    if module_name not in ('', '__main__'):
        json_class = '{0}.{1}'.format(module_name, json_class)

    # Keep the class name in the returned object
    return_obj = {"__jsonclass__": [json_class, ]}

    # If a serialization method is defined..
    if serialize_method in dir(obj):
        # Params can be a dict (keyword) or list (positional)
        # Attrs MUST be a dict.
        serialize = getattr(obj, serialize_method)
        params, attrs = serialize()
        return_obj['__jsonclass__'].append(params)
        return_obj.update(attrs)
        return return_obj

    else:
        # Otherwise, try to figure it out
        # Obviously, we can't assume to know anything about the
        # parameters passed to __init__
        return_obj['__jsonclass__'].append([])
        attrs = {}
        ignore_list = getattr(obj, ignore_attribute, []) + ignore
        for attr_name, attr_value in obj.__dict__.items():
            if isinstance(attr_value, supported_types) and \
                    attr_name not in ignore_list and \
                    attr_value not in ignore_list:
                attrs[attr_name] = dump(attr_value, serialize_method,
                                        ignore_attribute, ignore)
        return_obj.update(attrs)
        return return_obj


def load(obj, classes=None):
    """
    If 'obj' is a dictionary containing a __jsonclass__ entry, converts the
    dictionary item into a bean of this class.

    :param obj: An object from a JSON-RPC dictionary
    :param classes: A custom {name: class} dictionary
    :return: The loaded object
    """
    # Primitive
    if isinstance(obj, utils.primitive_types):
        return obj

    # List, set or tuple
    elif isinstance(obj, utils.iterable_types):
        return_obj = [load(entry) for entry in obj]
        if isinstance(obj, utils.TupleType):
            return_obj = tuple(return_obj)

        return return_obj

    # Otherwise, it's a dict type
    elif '__jsonclass__' not in obj.keys():
        return_dict = {}
        for key, value in obj.items():
            return_dict[key] = load(value)
        return return_dict

    # It's a dict, and it has a __jsonclass__
    orig_module_name = obj['__jsonclass__'][0]
    params = obj['__jsonclass__'][1]

    # Validate the module name
    if not orig_module_name:
        raise TranslationError('Module name empty.')

    json_module_clean = re.sub(invalid_module_chars, '', orig_module_name)
    if json_module_clean != orig_module_name:
        raise TranslationError('Module name {0} has invalid characters.' \
                               .format(orig_module_name))

    # Load the class
    json_module_parts = json_module_clean.split('.')
    json_class = None
    if classes and len(json_module_parts) == 1:
        # Local class name -- probably means it won't work
        try:
            json_class = classes[json_module_parts[0]]
        except KeyError:
            raise TranslationError('Unknown class or module {0}.' \
                                   .format(json_module_parts[0]))

    else:
        # Module + class
        json_class_name = json_module_parts.pop()
        json_module_tree = '.'.join(json_module_parts)
        try:
            # Use fromlist to load the module itself, not the package
            temp_module = __import__(json_module_tree,
                                     fromlist=[json_class_name])
        except ImportError:
            raise TranslationError('Could not import {0} from module {1}.' \
                                   .format(json_class_name, json_module_tree))

        try:
            json_class = getattr(temp_module, json_class_name)

        except AttributeError:
            raise TranslationError("Unknown class {0}.{1}." \
                                   .format(json_module_tree, json_class_name))

    # Create the object
    new_obj = None
    if isinstance(params, utils.ListType):
        try:
            new_obj = json_class(*params)

        except TypeError as ex:
            raise TranslationError("Error instantiating {0}: {1}"\
                                   .format(json_class.__name__, ex))

    elif isinstance(params, utils.DictType):
        try:
            new_obj = json_class(**params)

        except TypeError as ex:
            raise TranslationError("Error instantiating {0}: {1}"\
                                   .format(json_class.__name__, ex))

    else:
        raise TranslationError("Constructor args must be a dict or a list, "
                               "not {0}".format(type(params).__name__))

    # Remove the class information, as it must be ignored during the
    # reconstruction of the object
    del obj['__jsonclass__']

    for key, value in obj.items():
        setattr(new_obj, key, value)

    return new_obj

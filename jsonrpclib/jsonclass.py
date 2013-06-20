#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
The serialization module
"""

__version__ = "0.1.5"

# ------------------------------------------------------------------------------

# Local package
from jsonrpclib import config
import jsonrpclib.utils as utils

# Standard library
import inspect
import re

# ------------------------------------------------------------------------------

# Supported transmitted code
supported_types = utils.iter_types + utils.primitive_types

# Regex of invalid module characters
invalid_module_chars = r'[^a-zA-Z0-9\_\.]'

# ------------------------------------------------------------------------------

class TranslationError(Exception):
    """
    Unmarshaling exception
    """
    pass

# ------------------------------------------------------------------------------

def dump(obj, serialize_method=None, ignore_attribute=None, ignore=[]):
    """
    Transforms the given object into a JSON-RPC compliant form.
    Converts beans into dictionaries with a __jsonclass__ entry.
    Doesn't change primitive types.
    
    :param obj: An object to convert
    :param serialize_method: Custom serialization method
    :param ignore_attribute: Name of the object attribute containing the names
                             of members to ignore
    :param ignore: A list of members to ignore
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
    if isinstance(obj, utils.iter_types):

        if isinstance(obj, utils.DictType):
            # It's a dictionary
            new_obj = {}
            for key, value in obj.items():
                new_obj[key] = dump(value, serialize_method,
                                     ignore_attribute, ignore)
            return new_obj

        else:
            # ... list or tuple
            new_obj = []
            for item in obj:
                new_obj.append(dump(item, serialize_method,
                                     ignore_attribute, ignore))

            if isinstance(obj, utils.TupleType):
                # Keep the "tuple" type
                new_obj = tuple(new_obj)

            return new_obj

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


def load(obj):
    """
    If 'obj' is a dictionary containing a __jsonclass__ entry, converts the
    dictionary item into a bean of this class.
    
    :param obj: An object from a JSON-RPC dictionary
    :return: The loaded object
    """
    # Primitive
    if isinstance(obj, utils.primitive_types):
        return obj

    # List
    elif isinstance(obj, (utils.ListType, utils.TupleType)):
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
    if len(json_module_parts) == 1:
        # Local class name -- probably means it won't work
        if json_module_parts[0] not in config.classes.keys():
            raise TranslationError('Unknown class or module {0}.' \
                                   .format(json_module_parts[0]))
        json_class = config.classes[json_module_parts[0]]

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
        new_obj = json_class(*params)

    if isinstance(params, utils.DictType):
        new_obj = json_class(**params)

    else:
        raise TranslationError('Constructor args must be a dict or list.')

    for key, value in obj.items():
        if key == '__jsonclass__':
            # Ignore the __jsonclass__ member
            continue

        setattr(new_obj, key, value)

    return new_obj

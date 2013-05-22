#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# ------------------------------------------------------------------------------

setup(
    name="jsonrpclib-pelix",
    version="0.1.4",
    packages=["jsonrpclib"],
    author="Thomas Calmant",
    author_email="thomas.calmant@gmail.com",
    url="http://github.com/tcalmant/jsonrpclib/",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    description="Fork of jsonrpclib by Josh Marshall, usable with Pelix " \
                "remote services." \
                "This project is an implementation of the JSON-RPC v2.0 " \
                "specification (backwards-compatible) as a client library.",
    long_description=open("README.md").read()
)

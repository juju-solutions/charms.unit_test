## Overview

This library contains tools for unit testing layered charms.

One of the challenges of developing a layered charm is that you may reference Python modules from other layers in an import, but those modules will not be available to you until you run "charm build" on your charm. This is expected, and works as intended for deployment and integration, but it is not ideal to wait for the charm to build every time you want to run unit tests, which are mean to be lightweight and swift to execute.

You can use Python tools like ``mock`` to patch our references to those missing modules at run time, but it is difficult to fix the ImportErrors that get raised when you try to import the modules at import time. The ``Harness`` class in this module addresses this problem with a ``patch_imports`` context that will suppress the import errors, allowing you to then using normal mocking tools to run your tests.

Additionally, the ``Harness`` class inherits from unittest.TestCase, and you can subclass it to produce your own test classes. If you do so, ``Harness`` will automagically setup mocks for ``charms.layer.options``, and provide a mocked out helper for ``hookenv.status_set``. This saves you from repeatedly mocking out these commonly used routines. ``Harness`` saves these automagic mocks in a convenient internal dict, so that you can add behavior to them, as you would any other ``mock.Mock`` object.

## Usage

(See the docstring in charms/unit/harness.py:Harness for now -- more details coming to the README later.)
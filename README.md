# Overview

This library contains tools for unit testing layered charms.

One of the challenges of developing a layered charm is that you may reference modules from other layers in an import, but those modules will not be available to you until you run "charm build" on your charm. This is fine for the case where you want to build your charm and actually use it, or run integration tests on it, but it is tedious to wait for a charm to build every time you want to run unit tests, which are mean to be lightweight and swift to execute.

The Harness class in this library solves this problem by examining your source tree, and automatically mocking out imports from other layers. The class exposes the mocks in a convenient dictionary, so that you can add behavior to them, and it also automatically sets mocks for other common use cases, such as calling the status tools in hookenv.

# Example Usage

```
from charms.unit.harness import Harness

from mycharm import Foo

class FooTest(Harness):

    def test_bar(self):
        '''Test a method that sets a status'''
        foo = Foo()
        foo.bar()
        self.assertEqual(self.last_status, ('active', 'bar ready'))
        
```
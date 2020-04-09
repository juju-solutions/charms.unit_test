import os
import sys
import importlib.util
from importlib import import_module
from importlib.machinery import ModuleSpec
from itertools import accumulate
from unittest.mock import MagicMock, patch

import pytest


try:
    ModuleNotFoundError
except NameError:
    # python 3.5 compatibility
    ModuleNotFoundError = ImportError


def _debug(msg, *args, color=None, **kwargs):
    pass  # used for debugging during testing only


def identity(x):
    return x


def module_ancestors(module_name):
    tree = list(accumulate(module_name.split('.'),
                           lambda a, b: '.'.join([a, b])))
    return tree[:-1]


class MockPackage(MagicMock):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, name=name, **kwargs)
        self.__name__ = name
        self.__path__ = []

    def _get_child_mock(self, **kw):
        return MagicMock(**kw)


class AutoImportMockPackage(MockPackage):
    def __getattr__(self, attr):
        if attr.startswith('_'):
            return super().__getattr__(attr)
        try:
            return import_module(self.__name__ + '.' + attr)
        except ModuleNotFoundError:
            return super().__getattr__(attr)


class MockFinder:
    def find_spec(self, fullname, path, target=None):
        """
        Find a ModuleSpec for the given module / package name.

        This can be called for one of two cases:

          * Nothing in this module tree has been loaded, in which case we'll be
            called for the top-level package name. In this case, we need to
            patch the entire module tree, but that is handled by MockLoader.

          * An ancestor has been loaded but the finder for that ancestor either
            is the MockFinder or it's one of the standard finders which can't
            find the requested module.
        """
        _debug('Searching for {}', fullname, color='cyan')
        # Defer to things actually on disk. To do so, though, we have to
        # temporarily remove any patched modules from sys.modules, or they will
        # prevent the normal discovery method from working. We also have to
        # temporarily remove this finder from sys.meta_path to prevent infinite
        # recursion. This handles the case where one of the ancestors is a
        # patched module, but the user is trying to import a real module. A
        # common example of this is having charms.layer patched but wanting to
        # import the charm's own lib code, from, e.g., charms.layer.my_charm.
        with patch.dict(sys.modules, clear=True,
                        values={name: mod for name, mod in sys.modules.items()
                                if not isinstance(mod, MockPackage)}):
            with patch('sys.meta_path',
                       [finder for finder in sys.meta_path
                        if not isinstance(finder, MockFinder)]):
                try:
                    file_spec = importlib.util.find_spec(fullname)
                    if file_spec:
                        _debug('Found real module {}', fullname, color='green')
                        return file_spec
                except ModuleNotFoundError:
                    pass

        # If nothing can be found on disk, then we're either being called as
        # a last option for something that really should fail, or because an
        # ancestor was patched and the user is expecting to be able to import
        # a submodule. In the former case, we should just fail as well. In the
        # latter case, we should automatically apply the patch so that it does
        # what they expect. A common case of that is the charm importing
        # a layer they depend on; since we don't want to have to explicitly
        # patch every possible layer, this allows us to auto-patch layers as
        # they're used.
        for module_name in reversed(module_ancestors(fullname)):
            existing_module = sys.modules.get(module_name)
            if not existing_module:
                continue
            if isinstance(existing_module, MockPackage):
                _debug('Found patched ancestor of {} at {}',
                       fullname, module_name, color='green')
                return ModuleSpec(fullname, MockLoader)
            # If we encounter a real module, we don't want to auto-mock
            # anything below it, even if an earlier ancestor is mocked.
            break
        _debug('No match found for {}', fullname, color='red')
        return None


class MockLoader:
    @classmethod
    def load_module(cls, fullname, replacement=None):
        """"Load" a mock module into sys.modules."""
        replacement = replacement or MockPackage(fullname)
        sys.modules[fullname] = replacement
        if '.' in fullname:
            # Attach the new "module" to its parent.
            parent_name, parent_attr = fullname.rsplit('.', 1)
            setattr(sys.modules[parent_name], parent_attr,
                    sys.modules[fullname])
        _debug('Patched {}', fullname, color='green')
        return replacement


def patch_module(fullname, replacement=None):
    """
    Patch a module (and potentially all of its parent packages).

    If replacement is given, it should inherit from MockPackage and will be
    used instead of a newly created MockPackage instance.
    """
    for ancestor in module_ancestors(fullname):
        if ancestor not in sys.modules:
            MockLoader.load_module(ancestor)
    return MockLoader.load_module(fullname, replacement)


def patch_fixture(patch_target, patch_opts=None, **kwargs):
    """
    Create a pytest fixture which patches the target.

    An optional ``patch_opts`` dict can be give, to be passed in to the call to
    ``patch``. Any other keyword args are passed to ``pytest.fixture``.
    """
    @pytest.fixture(**kwargs)
    def _fixture():
        with patch(patch_target, **(patch_opts or {})) as m:
            yield m
    return _fixture


def patch_reactive():
    """
    Setup the standard patches that any reactive charm will require.
    """
    patch_module('charms.templating')
    patch_module('charms.layer', AutoImportMockPackage(name='charms.layer'))

    ch = patch_module('charmhelpers')
    ch.hookenv.atexit = identity

    reactive = patch_module('charms.reactive')
    reactive.when.return_value = identity
    reactive.when_any.return_value = identity
    reactive.when_not.return_value = identity
    reactive.when_none.return_value = identity
    reactive.hook.return_value = identity

    os.environ['JUJU_MODEL_UUID'] = 'test-1234'
    os.environ['JUJU_UNIT_NAME'] = 'test/0'


sys.meta_path.append(MockFinder())

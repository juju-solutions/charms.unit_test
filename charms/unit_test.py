import os
import sys
import importlib.util
from importlib import import_module
from importlib.machinery import ModuleSpec
from itertools import accumulate
from unittest.mock import MagicMock, patch


try:
    ModuleNotFoundError
except NameError:
    # python 3.5 compatibility
    ModuleNotFoundError = ImportError


def identity(x):
    return x


def module_tree(module_name):
    return accumulate(module_name.split('.'), lambda a, b: '.'.join([a, b]))


class MockPackage(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__path__ = []
        if 'name' in kwargs:
            self.__name__ = kwargs['name']
        elif len(args) >= 5:
            self.__name__ = args[4]
        else:
            self.__name__ = ''

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
        # defer to things actually on disk; to do so, though, we have to
        # temporarily remove any patched modules from sys.modules, or they will
        # prevent the normal discovery method from working, as well as
        # temporarily removing this finder from sys.meta_path to prevent
        # infinite recursion
        with patch.dict(sys.modules, clear=True,
                        values={name: mod for name, mod in sys.modules.items()
                                if not isinstance(mod, MockPackage)}):
            with patch('sys.meta_path',
                       [finder for finder in sys.meta_path
                        if not isinstance(finder, MockFinder)]):
                try:
                    file_spec = importlib.util.find_spec(fullname)
                    if file_spec:
                        return file_spec
                except ModuleNotFoundError:
                    pass
        # otherwise, see if we've patched something related
        for method in (self._find_exact,
                       self._find_patched_parent,
                       self._find_patched_child):
            if method(fullname):
                return ModuleSpec(fullname, MockLoader())
        else:
            return None

    def _find_exact(self, fullname):
        """
        Handle the case of importing foo.bar when foo.bar is patched.
        """
        if fullname in sys.modules:
            assert isinstance(sys.modules[fullname], MockPackage)
            return True
        else:
            return False

    def _find_patched_parent(self, fullname):
        """
        Handle the case of importing foo.bar when foo is patched.
        """
        for module_name in module_tree(fullname):
            if isinstance(sys.modules.get(module_name), MockPackage):
                return True
        else:
            return False

    def _find_patched_child(self, fullname):
        """
        Handle the case of importing foo when foo.bar.qux is patched.
        """
        for module_name, module in sys.modules.items():
            if not isinstance(module, MockPackage):
                continue
            if module_name.startswith(fullname + '.'):
                return True
        else:
            return False


class MockLoader:
    def load_module(self, fullname, replacement=...):
        if replacement is ...:
            replacement = MockPackage(name=fullname)
        # in addition to the module we've been asked to load, we need to ensure
        # that each parent of the module is present and attached together
        for module_name in module_tree(fullname):
            if module_name not in sys.modules:
                sys.modules[module_name] = replacement
                if '.' in module_name:
                    # attach mock module to parent
                    parent_name, sub_name = module_name.rsplit('.', 1)
                    setattr(sys.modules[parent_name], sub_name, replacement)
        return replacement


sys.meta_path.append(MockFinder())


def patch_module(module_name, replacement=...):
    if module_name in sys.modules:
        mock_module = sys.modules[module_name]
        if not isinstance(mock_module, MockPackage):
            raise ValueError('already imported: {}'.format(module_name))
        return mock_module
    return MockLoader().load_module(module_name, replacement)


def patch_reactive():
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

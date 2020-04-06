import os
import sys
from importlib.machinery import ModuleSpec
from itertools import accumulate
from unittest.mock import MagicMock


def identity(x):
    return x


def module_tree(module_name):
    return accumulate(module_name.split('.'), lambda a, b: '.'.join([a, b]))


class MockPackage(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__path__ = []

    def _get_child_mock(self, **kw):
        return MagicMock(**kw)


class MockFinder:
    def find_spec(self, fullname, path, target=None):
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
    def load_module(self, fullname):
        # in addition to the module we've been asked to load, we need to ensure
        # that each parent of the module is present and attached together
        for module_name in module_tree(fullname):
            if module_name not in sys.modules:
                mock_module = MockPackage(name=module_name)
                sys.modules[module_name] = mock_module
                if '.' in module_name:
                    # attach mock module to parent
                    parent_name, sub_name = module_name.rsplit('.', 1)
                    setattr(sys.modules[parent_name], sub_name, mock_module)


sys.meta_path.append(MockFinder())


def patch_module(module_name):
    if module_name in sys.modules:
        mock_module = sys.modules[module_name]
        assert isinstance(mock_module, MockPackage)
        return mock_module
    return MockLoader().load_module(module_name)


def patch_reactive():
    patch_module('charms.templating')
    patch_module('charms.layer')

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

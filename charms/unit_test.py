import os
import sys
import importlib.util
from contextlib import contextmanager
from importlib.machinery import ModuleSpec
from itertools import accumulate, chain
from unittest.mock import DEFAULT, MagicMock, patch

import pytest


try:
    ModuleNotFoundError
except NameError:
    # python 3.5 compatibility
    ModuleNotFoundError = ImportError


def _debug_noop(msg, *args, color=None, **kwargs):
    pass


def _debug_pront(msg, *args, color=None, **kwargs):
    colors = {
        "red": "\x1b[31m",
        "green": "\x1b[32m",
        "yellow": "\x1b[33m",
        "blue": "\x1b[34m",
        "magenta": "\x1b[35m",
        "cyan": "\x1b[36m",
    }
    if color:
        msg = colors[color] + msg + "\x1b[0m"
    print(msg.format(*args, **kwargs))


_debug = _debug_noop  # overridden during testing by the --debug-tests option

flags = set()


def identity(x, *args, **kwargs):
    return x


def module_ancestors(module_name):
    tree = list(accumulate(module_name.split("."), lambda a, b: ".".join([a, b])))
    return tree[:-1]


class AutoImportMockPackage(MagicMock):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, name=name, **kwargs)
        self.__name__ = name
        self.__path__ = []

    def _get_child_mock(self, **kw):
        return MagicMock(**kw)

    def __getattr__(self, attr):
        if attr.startswith("_"):
            return super().__getattr__(attr)
        module_name = self.__name__ + "." + attr
        _debug("Attempting to auto-load {}", module_name, color="cyan")
        real_spec = MockFinder.find_real(module_name)
        if real_spec:
            module = importlib.import_module(module_name)
            setattr(self, attr, module)
            _debug("Loaded {}", module, color="green")
            return module
        else:
            _debug("Nothing to load for {}, returning mock", module_name, color="red")
            return super().__getattr__(attr)


@contextmanager
def _hide_patched_modules():
    # NB: can't use unittest.mock.patch.dict because it doesn't restore
    # attribute attachment.
    patches = {}
    for name, mod in sys.modules.items():
        if isinstance(mod, MagicMock):
            patches[name] = mod
    for name in patches.keys():
        del sys.modules[name]
    try:
        yield
    finally:
        for name, mod in sorted(patches.items()):
            sys.modules[name] = mod
            if "." in name:
                parent, attr = name.rsplit(".", 1)
                setattr(sys.modules[parent], attr, mod)


class MockFinder:
    @classmethod
    def find_real(cls, fullname):
        # Defer to things actually on disk. To do so, though, we have to
        # temporarily remove any patched modules from sys.modules, or they will
        # prevent the normal discovery method from working. We also have to
        # temporarily remove this finder from sys.meta_path to prevent infinite
        # recursion. This handles the case where one of the ancestors is a
        # patched module, but the user is trying to import a real module. A
        # common example of this is having charms.layer patched but wanting to
        # import the charm's own lib code, from, e.g., charms.layer.my_charm.
        with _hide_patched_modules():
            with patch(
                "sys.meta_path",
                [
                    finder
                    for finder in sys.meta_path
                    if not isinstance(finder, MockFinder)
                ],
            ):
                try:
                    file_spec = importlib.util.find_spec(fullname)
                    if file_spec:
                        _debug("Found real module {}", fullname, color="green")
                        return file_spec
                except ModuleNotFoundError:
                    pass

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
        _debug("Searching for {}", fullname, color="cyan")
        file_spec = self.find_real(fullname)
        if file_spec:
            return file_spec

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
            if isinstance(existing_module, MagicMock):
                _debug(
                    "Found patched ancestor of {} at {}",
                    fullname,
                    module_name,
                    color="green",
                )
                return ModuleSpec(fullname, MockLoader)
            # If we encounter a real module, we don't want to auto-mock
            # anything below it, even if an earlier ancestor is mocked.
            break
        _debug("No match found for {}", fullname, color="red")
        return None


class MockLoader:
    @classmethod
    def load_module(cls, fullname, replacement=None):
        """ "Load" a mock module into sys.modules."""
        if "." in fullname:
            parent_name, attr = fullname.rsplit(".", 1)
            parent = sys.modules[parent_name]
            if replacement is None:
                if isinstance(parent, MagicMock):
                    # Get the MockPackage from the parent, since it might have
                    # been imported elsewhere as an attribute (i.e., using the
                    # `from foo import bar` syntax). Also, we can't use getattr
                    # in case the parent is an AutoImportMockPackage because it
                    # will lead to infinite recursion.
                    try:
                        replacement = MagicMock.__getattribute__(parent, attr)
                    except AttributeError:
                        replacement = MagicMock.__getattr__(parent, attr)
                else:
                    replacement = MagicMock(name=fullname)
                    setattr(parent, attr, replacement)
            else:
                # We have a specific replacement, so attach it to the parent.
                setattr(parent, attr, replacement)
        elif replacement is None:
            replacement = MagicMock(name=fullname)
        # Turn mock into a "package".
        if not hasattr(replacement, "__path__"):
            replacement.__name__ = fullname
            replacement.__path__ = []
        if not hasattr(replacement, "__spec__"):
            replacement.__spec__ = ModuleSpec(fullname, cls)
        sys.modules[fullname] = replacement
        _debug("Patched {}", fullname, color="green")
        return replacement


def patch_module(fullname, replacement=None):
    """
    Patch a module (and potentially all of its parent packages).
    """
    patched = []

    def _unpatch(*_):
        for module_name in patched:
            del sys.modules[module_name]

    for ancestor in module_ancestors(fullname):
        if ancestor not in sys.modules:
            MockLoader.load_module(ancestor)
            patched.append(ancestor)
    patched.append(fullname)
    replacement = MockLoader.load_module(fullname, replacement)
    replacement.__enter__ = lambda s: replacement
    replacement.__exit__ = _unpatch
    return replacement


def patch_fixture(patch_target, new=DEFAULT, patch_opts=None, fixture_opts=None):
    """
    Create a pytest fixture which patches the target.

    The `new` param is equivalent to `patch_opts={'new': new}`, where
    `patch_opts` is a dict of kwargs to pass to the patch call.  Equivalently,
    `fixture_opts` is a dict of kwargs to pass to the fixture decorator.
    """
    fixture_opts = fixture_opts or {}
    patch_opts = patch_opts or {}
    if new is not DEFAULT:
        patch_opts["new"] = new

    @pytest.fixture(**fixture_opts)
    def _fixture():
        with patch(patch_target, **patch_opts) as m:
            yield m

    return _fixture


class _UnitList(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received = self[0].received if self else {}
        self.received_raw = self[0].received_raw if self else {}


class MockEndpoint(MagicMock):
    def __init__(self, endpoint_name, relation_ids=None):
        super().__init__()
        self.is_joined = False
        self._endpoint_name = endpoint_name
        self.relations = []
        if relation_ids:
            self.relations = [
                MagicMock(
                    relation_id=rel_id,
                    to_publish={},
                    to_publish_raw={},
                    joined_units=_UnitList([MagicMock(received={}, received_raw={})]),
                )
                for rel_id in relation_ids
            ]
        self.all_joined_units = _UnitList(
            chain.from_iterable(r.joined_units for r in self.relations)
        )

    @property
    def endpoint_name(self):
        return self._endpoint_name

    def expand_name(self, flag):
        return flag.replace("{endpoint_name}", self.endpoint_name)

    def _get_child_mock(self, **kwargs):
        return MagicMock(**kwargs)


class MockKV(dict):
    def set(self, key, value):
        self[key] = value

    def getrange(self, key_prefix, strip=False):
        results = {}
        strip_len = len(key_prefix) if strip else 0
        for key, value in self.items():
            if key.startswith(key_prefix):
                results[key[strip_len:]] = value
        return results

    def unset(self, key):
        self.pop(key, None)

    def unsetrange(self, keys=None, prefix=""):
        if keys is None:
            for key in [key for key in self.keys() if key.startswith(prefix)]:
                del self[key]
        else:
            for key in keys:
                self.pop(prefix + key, None)


def patch_reactive():
    """
    Setup the standard patches that any reactive charm will require.
    """
    patch_module("charms.templating")

    charms_layer = AutoImportMockPackage(name="charms.layer")
    charms_layer.import_layer_libs = MagicMock(name="import_layer_libs")
    patch_module("charms.layer", charms_layer)

    ch = patch_module("charmhelpers")
    ch.core.hookenv.atexit = identity
    ch.core.hookenv.charm_dir.return_value = "charm_dir"
    ch.core.host.restart_on_change.return_value = identity
    ch.core.unitdata.kv.return_value = MockKV()

    reactive = patch_module("charms.reactive")
    reactive.when.return_value = identity
    reactive.when_all.return_value = identity
    reactive.when_any.return_value = identity
    reactive.when_not.return_value = identity
    reactive.when_not_all.return_value = identity
    reactive.when_none.return_value = identity
    reactive.hook.return_value = identity
    reactive.set_flag.side_effect = flags.add
    reactive.clear_flag.side_effect = flags.discard
    reactive.set_state.side_effect = flags.add
    reactive.remove_state.side_effect = flags.discard
    reactive.toggle_flag.side_effect = lambda f, s: (
        flags.add(f) if s else flags.discard(f)
    )
    reactive.is_flag_set.side_effect = lambda f: f in flags
    reactive.is_state.side_effect = lambda f: f in flags
    reactive.get_flags.side_effect = lambda: sorted(flags)
    reactive.get_unset_flags.side_effect = lambda *f: sorted(set(f) - flags)

    reactive.Endpoint = MockEndpoint

    os.environ["JUJU_MODEL_UUID"] = "test-1234"
    os.environ["JUJU_UNIT_NAME"] = "test/0"
    os.environ["JUJU_MACHINE_ID"] = "0"
    os.environ["JUJU_AVAILABILITY_ZONE"] = ""

    return reactive


sys.meta_path.append(MockFinder())

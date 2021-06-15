import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from charms import unit_test


@pytest.fixture(autouse=True)
def clean_imports():
    sys_modules = sys.modules.copy()
    yield
    sys.modules.clear()
    sys.modules.update(sys_modules)


def test_patch():
    unit_test.patch_module("dummy")
    import dummy

    assert isinstance(dummy, MagicMock)
    assert isinstance(dummy.foo, MagicMock)


def test_patch_cm():
    with unit_test.patch_module("dummy.test.foo") as _foo:
        from dummy.test import foo

        assert foo is _foo
    with pytest.raises(ImportError):
        from dummy.test import foo


def test_patch_with_patched_ancestor():
    unit_test.patch_module("dummy")
    unit_test.patch_module("dummy.test")
    import dummy.test as dummy_test
    import dummy

    assert isinstance(dummy_test, MagicMock)
    assert dummy.test is dummy_test


def test_patch_with_real_ancestor():
    unit_test.patch_module("charms.dummy")
    import charms.dummy as charms_dummy
    import charms

    assert isinstance(charms_dummy, MagicMock)
    assert charms.dummy is charms_dummy


def test_unpatched_missing():
    with pytest.raises(ImportError):
        import dummy.test  # noqa


def test_unpatched_with_real_ancestor():
    with pytest.raises(ImportError):
        import charms.dummy.test  # noqa


def test_unpatched_with_patched_ancestor():
    unit_test.patch_module("dummy")
    from dummy import test
    import dummy.test.module as dummy_test_module

    assert isinstance(dummy_test_module, MagicMock)
    assert test.module is dummy_test_module


def test_unpatched_with_patched_child():
    unit_test.patch_module("dummy.test.module")
    import dummy.test
    import dummy.test.module as dummy_test_module

    assert isinstance(dummy.test, MagicMock)
    assert isinstance(dummy.test.module, MagicMock)
    assert dummy.test.module is dummy_test_module


def test_import_real_over_patched_ancestor():
    sys.path.insert(0, str(Path(__file__).parent / "lib"))
    unit_test.patch_module("patched.module")
    import patched.module.import_over_patch as import_over_patch
    import patched.module

    assert not isinstance(import_over_patch, MagicMock)
    assert isinstance(patched.module, MagicMock)
    assert import_over_patch.real_or_fake == "real"
    assert patched.module.import_over_patch is import_over_patch


@patch("sys.path", [str(Path(__file__).parent / "lib")] + sys.path)
def test_auto_import_mock_package():
    import patched

    mock_package = unit_test.AutoImportMockPackage(name="patched.module")
    unit_test.patch_module("patched.module", mock_package)
    assert not isinstance(patched.module.import_over_patch, MagicMock)
    assert isinstance(patched.module, MagicMock)
    assert patched.module.import_over_patch.real_or_fake == "real"


@patch("sys.path", [str(Path(__file__).parent / "lib")] + sys.path)
def test_auto_import_mock_package_from_syntax():
    import patched

    mock_package = unit_test.AutoImportMockPackage(name="patched.module")
    unit_test.patch_module("patched.module", mock_package)
    from patched.module import import_over_patch

    assert not isinstance(import_over_patch, MagicMock)
    assert isinstance(patched.module, MagicMock)
    assert import_over_patch.real_or_fake == "real"


@patch("sys.path", [str(Path(__file__).parent / "lib" / "patched")] + sys.path)
def test_auto_import_mock_package_top_level():
    mock_package = unit_test.AutoImportMockPackage(name="module")
    unit_test.patch_module("module", mock_package)
    import module

    assert not isinstance(module.import_over_patch, MagicMock)
    assert isinstance(module, MagicMock)
    assert module.import_over_patch.real_or_fake == "real"


def test_mock_endpoint():
    endpoint = unit_test.MockEndpoint("test")
    assert not endpoint.is_joined
    assert len(endpoint.relations) == 0
    assert len(list(endpoint.all_joined_units)) == 0
    endpoint = unit_test.MockEndpoint("test", [1, 2])
    assert len(endpoint.relations) == 2
    assert endpoint.relations[0].to_publish == {}
    assert len(list(endpoint.all_joined_units)) == 2
    assert endpoint.all_joined_units[0].received == {}
    assert (
        endpoint.all_joined_units.received
        is endpoint.all_joined_units[0].received
        is endpoint.relations[0].joined_units.received
        is endpoint.relations[0].joined_units[0].received
    )
    assert (
        endpoint.all_joined_units.received_raw
        is endpoint.all_joined_units[0].received_raw
        is endpoint.relations[0].joined_units.received_raw
        is endpoint.relations[0].joined_units[0].received_raw
    )
    assert endpoint.expand_name("{endpoint_name}.foo") == "test.foo"


def test_mock_kv():
    kv = unit_test.MockKV()
    assert kv == {}
    kv.set("foo", "bar")
    # Adapted from charmhelpers test
    kv.set("docker.net_mtu", 1)
    kv.set("docker.net_nack", True)
    kv.set("docker.net_type", "vxlan")
    assert kv.getrange("docker") == {
        "docker.net_mtu": 1,
        "docker.net_type": "vxlan",
        "docker.net_nack": True,
    }
    assert kv.getrange("docker.", True) == {
        "net_mtu": 1,
        "net_type": "vxlan",
        "net_nack": True,
    }
    kv.unset("foo")
    assert kv == {
        "docker.net_mtu": 1,
        "docker.net_type": "vxlan",
        "docker.net_nack": True,
    }
    kv.unsetrange(["net_mtu"], "docker.")
    assert kv == {
        "docker.net_type": "vxlan",
        "docker.net_nack": True,
    }
    kv.set("foo", "bar")
    kv.unsetrange(prefix="docker.")
    assert kv == {"foo": "bar"}


def test_patch_reactive():
    unit_test.patch_reactive()
    import charms
    import charms.templating  # noqa
    import charms.layer.foo  # noqa
    import charmhelpers
    from charms.layer import import_layer_libs  # noqa
    from charms.reactive import when, when_all, when_not_all
    from charms.reactive import set_flag, clear_flag, is_flag_set
    from charms.reactive import get_flags, get_unset_flags
    from charms.reactive import set_state, remove_state, is_state
    from charms.reactive import toggle_flag

    @charmhelpers.core.hookenv.atexit
    def test_atexit():
        return "ok"

    assert test_atexit() == "ok"

    @when("foo")
    def test_when():
        return "ok"

    assert test_when() == "ok"

    @when_all("foo", "bar")
    def test_when_all():
        return "all_ok"

    assert test_when_all() == "all_ok"

    @when_not_all("foo", "bar", "baz")
    def test_when_not_all():
        return "not_all_ok"

    assert test_when_not_all() == "not_all_ok"

    assert not is_flag_set("foo")
    assert not is_state("foo")
    set_flag("foo")
    assert is_flag_set("foo")
    assert is_state("foo")
    clear_flag("foo")
    assert not is_flag_set("foo")
    assert not is_state("foo")
    set_state("foo")
    assert is_flag_set("foo")
    assert is_state("foo")
    remove_state("foo")
    assert not is_flag_set("foo")
    assert not is_state("foo")
    toggle_flag("foo", False)
    assert not is_flag_set("foo")
    toggle_flag("foo", True)
    assert is_flag_set("foo")

    assert get_flags() == ["foo"]
    assert get_unset_flags("foo", "bar") == ["bar"]

    assert charms.layer.import_layer_libs

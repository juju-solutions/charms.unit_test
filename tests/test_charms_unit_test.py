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
    unit_test.patch_module('dummy')
    import dummy
    assert isinstance(dummy, MagicMock)
    assert isinstance(dummy.foo, MagicMock)


def test_patch_with_patched_ancestor():
    unit_test.patch_module('dummy')
    unit_test.patch_module('dummy.test')
    import dummy.test as dummy_test
    import dummy
    assert isinstance(dummy_test, MagicMock)
    assert dummy.test is dummy_test


def test_patch_with_real_ancestor():
    unit_test.patch_module('charms.dummy')
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
    unit_test.patch_module('dummy')
    from dummy import test
    import dummy.test.module as dummy_test_module
    assert isinstance(dummy_test_module, MagicMock)
    assert test.module is dummy_test_module


def test_unpatched_with_patched_child():
    unit_test.patch_module('dummy.test.module')
    import dummy.test
    import dummy.test.module as dummy_test_module
    assert isinstance(dummy.test, MagicMock)
    assert isinstance(dummy.test.module, MagicMock)
    assert dummy.test.module is dummy_test_module


def test_import_real_over_patched_ancestor():
    sys.path.insert(0, str(Path(__file__).parent / 'lib'))
    unit_test.patch_module('patched.module')
    import patched.module.import_over_patch as import_over_patch
    import patched.module
    assert not isinstance(import_over_patch, MagicMock)
    assert isinstance(patched.module, MagicMock)
    assert import_over_patch.real_or_fake == 'real'
    assert patched.module.import_over_patch is import_over_patch


@patch('sys.path', [str(Path(__file__).parent / 'lib')] + sys.path)
def test_auto_import_mock_package():
    import patched
    mock_package = unit_test.AutoImportMockPackage(name='patched.module')
    unit_test.patch_module('patched.module', mock_package)
    assert not isinstance(patched.module.import_over_patch, MagicMock)
    assert isinstance(patched.module, MagicMock)
    assert patched.module.import_over_patch.real_or_fake == 'real'


@patch('sys.path', [str(Path(__file__).parent / 'lib')] + sys.path)
def test_auto_import_mock_package_from_syntax():
    import patched
    mock_package = unit_test.AutoImportMockPackage(name='patched.module')
    unit_test.patch_module('patched.module', mock_package)
    from patched.module import import_over_patch
    assert not isinstance(import_over_patch, MagicMock)
    assert isinstance(patched.module, MagicMock)
    assert import_over_patch.real_or_fake == 'real'


@patch('sys.path', [str(Path(__file__).parent / 'lib' / 'patched')] + sys.path)
def test_auto_import_mock_package_top_level():
    mock_package = unit_test.AutoImportMockPackage(name='module')
    unit_test.patch_module('module', mock_package)
    import module
    assert not isinstance(module.import_over_patch, MagicMock)
    assert isinstance(module, MagicMock)
    assert module.import_over_patch.real_or_fake == 'real'


def test_patch_reactive():
    unit_test.patch_reactive()
    import charms.templating  # noqa
    import charms.layer.foo  # noqa
    import charmhelpers
    from charms.reactive import when, when_all, when_not_all

    @charmhelpers.core.hookenv.atexit
    def test_atexit():
        return 'ok'
    assert test_atexit() == 'ok'

    @when('foo')
    def test_when():
        return 'ok'
    assert test_when() == 'ok'

    @when_all('foo', 'bar')
    def test_when_all():
        return 'all_ok'
    assert test_when_all() == 'all_ok'

    @when_not_all('foo', 'bar', 'baz')
    def test_when_not_all():
        return 'not_all_ok'
    assert test_when_not_all() == 'not_all_ok'

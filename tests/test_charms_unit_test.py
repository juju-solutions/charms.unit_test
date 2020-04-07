import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from charms import unit_test


@pytest.fixture(autouse=True)
def clean_imports():
    sys_modules = sys.modules.copy()
    yield
    sys.modules.clear()
    sys.modules.update(sys_modules)


def test_exact_match():
    unit_test.patch_module('dummy')
    import dummy
    assert isinstance(dummy, unit_test.MockPackage)
    assert isinstance(dummy.foo, MagicMock)


def test_patched_parent():
    unit_test.patch_module('dummy')
    import dummy.test
    assert isinstance(dummy.test, unit_test.MockPackage)
    assert isinstance(dummy.test.foo, MagicMock)


def test_patched_parent_existing_namespace():
    unit_test.patch_module('charms.dummy')
    import charms.dummy.test
    assert isinstance(charms.dummy.test, unit_test.MockPackage)
    assert isinstance(charms.dummy.test.foo, MagicMock)


def test_patched_child():
    unit_test.patch_module('dummy.test.module')
    import dummy.test
    assert isinstance(dummy.test.module, unit_test.MockPackage)
    assert isinstance(dummy.test.module.foo, MagicMock)


def test_import_over_patch():
    sys.path.insert(0, str(Path(__file__).parent / 'lib'))
    unit_test.patch_module('patched.module')
    from patched.module.import_over_patch import real_or_fake
    assert real_or_fake == 'real'


def test_auto_import_mock_package():
    sys.path.insert(0, str(Path(__file__).parent / 'lib'))
    mock_package = unit_test.AutoImportMockPackage(name='patched.module')
    unit_test.patch_module('patched.module', mock_package)
    import patched
    assert patched.module.import_over_patch.real_or_fake == 'real'

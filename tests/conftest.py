import pytest

from charms import unit_test


def pytest_addoption(parser):
    parser.addoption("--debug-tests", action="store_true")


@pytest.fixture(autouse=True)
def cmdopt(request):
    if request.config.getoption("--debug-tests"):
        unit_test._debug = unit_test._debug_pront

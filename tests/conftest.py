import pytest

from charms import unit_test


def pytest_addoption(parser):
    parser.addoption("--debug-tests", action="store_true")


@pytest.fixture(autouse=True)
def cmdopt(request):
    if request.config.getoption("--debug-tests"):
        unit_test._debug = _debug_pront


def _debug_pront(msg, *args, color=None, **kwargs):
    colors = {
        'red': '\x1b[31m',
        'green': '\x1b[32m',
        'yellow': '\x1b[33m',
        'blue': '\x1b[34m',
        'magenta': '\x1b[35m',
        'cyan': '\x1b[36m',
    }
    if color:
        msg = colors[color] + msg + '\x1b[0m'
    print(msg.format(*args, **kwargs))

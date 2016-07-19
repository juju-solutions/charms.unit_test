#
# harness.py -- Unit Testing Harness for Layered Charms
#
# copyright 2016 Canonical Ltd.
# TODO: License (Apache or LGPL?)
#

import sys

from contextlib import contextmanager
from glob import glob
import logging
import mock
import unittest

LOGGER = logging.getLogger()
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.DEBUG)


class Harness(unittest.TestCase):
    '''
    I am a unit testing harness for Juju Layered charms. I am useful
    if you are testing a layer that imports Python code from other
    layers. Those imports will not be available until you build the
    layer, which means that you must either build the charm before
    performing unit tests (slows you down), or use my built in import
    patcher and mocking automagic.

    Say that you are testing ``reactive/foo.py`` in your layer, which
    imports something from layer ``bar``. Here is how you might set up
    your tests:

    ```
    from charms.unit import Harness

    with Harness.patch_imports('charms.layer.bar'):
        from reactive.foo import Foo

    class TestFoo(Harness):
        ...
    ```

    After performing my import patching magic, I automatically patch
    out inline references to layer.options and hookenv.status_get in
    your source tree, saving you some explicit calls to
    mock.patch. The status_set mocks will actually set statuses that
    can be retrieved by checking my .last_status property.

    I keep a dict of all mocks that I have created. To access the
    options that I've mocked out for reactive/foo, you can find the
    mock by looking up the following:

    ```
    self.mocks['foo.layer.options']
    ```

    Note that the name of the mock is simply the path to your module,
    with a leading 'reactive' or 'lib' stripped off, plus
    'layer.options'

    '''
    @classmethod
    @contextmanager
    def patch_imports(*to_mock):
        '''
        Given a list of references to modules, in dot format, I'll add a
        mock object to sys.modules corresponding to that reference. When
        this context handler exits, I'll clean up the references.

        '''
        if type(to_mock[0]) is list:
            to_mock = to_mock[0]

        refs = {}

        for ref in to_mock:
            mock_mod = mock.Mock()
            refs[ref] = mock_mod
            sys.modules[ref] = mock_mod

        try:
            yield refs
        finally:
            for ref in to_mock:
                del sys.modules[ref]

    def __init__(self, *args, **kwargs):
        super(Harness, self).__init__(*args, **kwargs)

        # Private properties
        self._patchers = []
        self._local_modules = None
        self._log = LOGGER

        # List of mocks that I've created.
        self.mocks = {}
        # List of statuses that I've set.
        self.statuses = []
        # I will search the following directories for modules, and
        # automatically patch out 'layer.options' and
        # 'hookenv.status_set':
        self.search_dirs = ['reactive', 'lib/charms/layer']
        # 'lib' and 'reactive' are typically added to PYTHONPATH when
        # running tests, so I'll strip out that part of the module
        # name when setting up my mock patches.
        self.trim_prefixes = ['lib.', 'reactive.']

    def log(self, msg):
        '''
        Print a given message to STDOUT.

        '''
        self._log.debug(msg)

    def set_mock(self, ref, side_effect=None):
        '''
        Setup a mock patcher for a given reference. Possibly add a side effect.

        Returns the created mock object, and also stores it in self.mocks.

        '''
        patcher = mock.patch(ref, create=True)
        try:
            self.mocks[ref] = patcher.start()
        except AttributeError as e:
            self.log("AttributeError: {}".format(e))
        except ImportError as e:
            # TODO: I don't think that ignoring this is the right
            # thing to do (we get ImportErrors only in our test
            # modules; not sure whether it's an issue w/ the
            # artificiality of the test environment, or a real issue.)
            self.log("ImportError: {}".format(e))
        else:
            self._patchers.append(patcher)
            if side_effect:
                self.mocks[ref].side_effect = side_effect

            return self.mocks[ref]

    @property
    def last_status(self):
        '''
        Helper for mocked out status list.

        Returns the last status set, or a (None, None) tuple if no
        status has been set.

        '''
        if not self.statuses:
            return (None, None)
        return self.statuses[-1]

    def _status_set(self, status, message):
        '''Set our mock status.'''

        self.statuses.append((status, message))

    def mock_hookenv_status(self):
        '''
        Mock out references to hookenv.status_set, or just status_set in
        files we might want to test (depending on how it was imported).

        '''
        for mod in self.local_modules:
            for ref in ['{}.hookenv.status_set'.format(mod),
                        '{}.status_set'.format(mod)]:
                self.set_mock(ref, side_effect=self._status_set)

    def mock_layer_init(self):
        '''
        Mock out 'layer.options'.

        '''
        for mod in self.local_modules:
            self.set_mock('{}.layer'.format(mod))

    @property
    def local_modules(self):
        '''
        Searches the source tree for Python files. Returns a list of
        module names, each suitable for passing to mock.patch.

        This method will only run once per class instantiation.

        '''
        if self._local_modules is None:

            # Grab everything in reactive and lib/charms/layer
            mods = []
            for dir_ in self.search_dirs:
                mods.extend(glob('**{}/*.py'.format(dir_)))

            # Transform the file path into a Python module reference
            # (strip off '.py' extension)
            mods = [".".join(f[:-3].split("/")) for f in mods]

            # Get rid of parts of the module path that are already
            # part of PYTHONPATH, and therefore not part of the way
            # that Python references the modules.
            for prefix in self.trim_prefixes:
                mods = [f.split(prefix)[1] if prefix in f else f for f in mods]

            self.log("List of modules to automagic: {}".format(mods))

            self._local_modules = mods
        return self._local_modules

    def setUp(self):
        '''
        Setup all of our mocks. Do this during setUp instead of setUpClass
        so that each test has access to a clean list of mocks.

        '''
        self.mock_hookenv_status()
        self.mock_layer_init()

    def tearDown(self):
        '''Clean up our mocks.'''
        for patcher in self._patchers:
            patcher.stop()

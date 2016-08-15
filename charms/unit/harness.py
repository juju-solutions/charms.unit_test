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
    last_imports = []

    @classmethod
    @contextmanager
    def patch_imports(cls, *to_mock):
        '''
        Given a list of references to modules, in dot format, I'll add a
        mock object to sys.modules corresponding to that reference. When
        this context handler exits, I'll clean up the references.

        '''
        if type(to_mock[0]) in (list, tuple):
            to_mock = to_mock[0]

        cls.last_imports = to_mock

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
        self.trim_prefixes = ['lib.']

    def log(self, msg):
        '''
        Print a given message to STDOUT.

        '''
        self._log.debug(msg)

    def set_mock(self, ref, side_effect=None, return_value=None):
        '''
        Setup a mock patcher for a given reference. Possibly add a side effect.

        Returns the created mock object, and also stores it in self.mocks.

        '''
        patcher = mock.patch(ref, create=True)
        self.mocks[ref] = patcher.start()
        self._patchers.append(patcher)
        if side_effect:
            self.mocks[ref].side_effect = side_effect
        if return_value:
            self.mocks[ref].return_value = return_value

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
            if hasattr(sys.modules.get(mod), 'hookenv'):
                self.set_mock(
                    '{}.hookenv.status_set'.format(mod),
                    side_effect=self._status_set)

            if hasattr(sys.modules.get(mod), 'status_set'):
                self.set_mock(
                    '{}.status_set'.format(mod),
                    side_effect=self._status_set)

    def mock_options(self):
        '''
        Mock out 'layer.options'.

        '''
        for mod in self.local_modules:
            # Deal with the case where someone does 'from charms
            # import layer', and the case where they do 'from
            # charms.layer import options.'
            if hasattr(sys.modules.get(mod), 'layer'):
                self.set_mock('{}.layer'.format(mod))

            if hasattr(sys.modules.get(mod), 'options'):
                self.set_mock('{}.options'.format(mod))

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
        with self.patch_imports(self.last_imports):
            self.mock_hookenv_status()
            self.mock_options()

    def tearDown(self):
        '''Clean up our mocks.'''
        for patcher in self._patchers:
            patcher.stop()

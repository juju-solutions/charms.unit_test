#
# harness.py -- Unit Testing Harness for Layer Charms
#
# copyright 2016 Canonical Ltd.
# TODO: License (Apache or LGPL?)
#

from glob import glob
import mock
import unittest

class HarnessError(Exception): pass

class Harness(unittest.TestCase):
    '''
    I am a unit testing harness for Juju Layered charms.

    I automatically mock out any modules referenced in the layers
    directory that do not actually exist in the layer's source. I
    maintain an internal table of the mock objects, so that you may
    add behavior to them if necessary for a test.

    I will also setup a mock for the status handlers in hookenv, so
    that you may set and confirm status in a test.

    '''
    def __init__(self, *args, **kwargs):
        super(Harness, self).__init__(*args, **kwargs)
        self._to_mock = []
        self._patchers = []
        self._local_modules = None
        self.mocks = {}

    @property
    def last_status(self):
        '''
        Helper for mocked out status list.

        Returns the last status set. Raises a HarnessError if this
        method is called, but the hookenv mock is not active.

        '''
        try:
            return self.statuses[-1]
        except AttributeError:
            raise HarnessError(
                'self.statuses does not exist. Did you initialize a '
                'harness without passing in mock_hookenv_status=True?')

    @property
    def local_modules(self):
        '''
        Searches the source tree for Python files. Returns a list of
        module names, each suitable for passing to mock.patch.

        This method will only run once per class instantiation.

        '''
        if self._local_modules is None:
            # TODO: there is probably a more elegant way to do
            # this. At the very least, we probably want to handle
            # Python files without a .py extension.

            # Grab everything in reactive and lib/charms/layer
            mods = glob("**reactive/*.py", recursive=True)
            mods.extend(glob("**lib/charms/layer/*.py", recursive=True))

            # Transform the file path into a Python module reference
            # (strip off '.py' extension)
            mods = [".".join(f[:-3].split("/")) for f in mods]

            # Get rid of 'lib.' -- we'll typically append 'lib' to our
            # path for testing (nose appends it automatically), so it
            # won't ever be part of our module name.
            mods = [f[4:] if f.startswith("lib.") else f for f in mods]

            self._local_modules = mods
        return self._local_modules

    def setUp(self, to_mock=None, mock_hookenv_status=True, mock_layers=True):
        '''
        Setup all of our mocks. Do this during setUp instead of setUpClass
        so that each test has access to a clean list of mocks.

        @param list to_mock: This class will automatically compose a
            list of modules to mock out. If you need to mock out
            additional modules, you may pass them in here.
        @param bool mock_hookenv_status: Set to False if you want to
            avoid mocking out calls to the hookenv lib.
        @param bool mock_layers: Set to False if you want to skip
            mocking out calls to layers that aren't checked into this
            layer's source tree.

        '''

        self._to_mock.extend(to_mock or [])

        if mock_layers:
            for f in self.local_modules:
                print("to mock: {}".format(f))
                self._to_mock.append('{}.layer'.format(f))

        if mock_hookenv_status:
            self.statuses = []
            for f in self.local_modules:
                self._to_mock.append('{}.hookenv'.format(f))

        # Attempt to patch all of the references that we've found.  If
        # a reference fails (because the file doesn't actually import
        # the thing that we're patching), just skip.
        for ref in self._to_mock:
            patcher = mock.patch(ref)
            try:
                self.mocks[ref] = patcher.start()
            except AttributeError:
                pass
            else:
                self._patchers.append(patcher)

    def tearDown(self):
        for patcher in self._patchers:
            patcher.stop()

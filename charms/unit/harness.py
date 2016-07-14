#
# harness.py -- Unit Testing Harness for Layered Charms
#
# copyright 2016 Canonical Ltd.
# TODO: License (Apache or LGPL?)
#

from contextlib import contextmanager
from glob import glob
import mock
import sys
import unittest


class Harness(unittest.TestCase):
    '''
    I am a unit testing harness for Juju Layered charms.

    The most import thing that I do is expose a patch_imports context
    that allows you to patch references to code that doesn't exist in
    your layer with mocks.

    This is useful if you are importing something from another
    layer. Say you are testing reactive/foo.py, and you
    are importing something from layer bar like so:

    ```
    from charms.layers.bar import Bar
    ```

    layers/bar.py is not in your source tree, however, because it
    exists only in another layer. In your test, you could do the
    following to fix the import error:

    ```
    from charms.unit import Harness:

    with Harness.patch_imports('charms.layer.bar'):
    from reactive.foo import Foo
    ```

    I also automatically patch references to hookenv.status_get in
    test classes that inherit from me. You can access the latest
    status set by checking my .last_status property.

    '''

    @classmethod
    @contextmanager
    def patch_imports(*to_mock):
        '''
        Given a list of references to modules, in dot format, I'll add a
        mock object to sys.modules corresponding to that reference. When
        this context handler exits, I'll clean up the references.

        TODO: just make this into a generator and store it in this
        class.

        '''
        if type(to_mock[0]) is list:
            to_mock = to_mock[0]

        for ref in to_mock:
            sys.modules[ref] = mock.Mock()

        try:
            yield to_mock
        finally:
            pass
            #for ref in to_mock:
            #    del sys.modules[ref]

    def __init__(self, *args, **kwargs):
        super(Harness, self).__init__(*args, **kwargs)
        self._patchers = []
        self._local_modules = None
        self.mocks = {}
        self.statuses = []

    def set_mock(self, ref, side_effect=None):
        '''
        Setup a mock patcher for a given reference. Possibly add a side effect.

        '''
        patcher = mock.patch(ref, create=True)
        try:
            self.mocks[ref] = patcher.start()
        except AttributeError:
            pass
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
        files we might want to test.

        '''
        for mod in self.local_modules:
            for ref in ['{}.hookenv.status_set'.format(mod),
                        '{}.status_set'.format(mod)]:
                self.set_mock(ref, side_effect=self._status_set)

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
            mods = glob("**reactive/*.py")
            mods.extend(glob("**lib/charms/layer/*.py"))

            # Transform the file path into a Python module reference
            # (strip off '.py' extension)
            mods = [".".join(f[:-3].split("/")) for f in mods]

            # Get rid of 'lib.' -- we'll typically append 'lib' to our
            # path for testing (nose appends it automatically), so it
            # won't ever be part of our module name.
            mods = [f[4:] if f.startswith("lib.") else f for f in mods]

            self._local_modules = mods
        return self._local_modules

    def setUp(self):
        '''
        Setup all of our mocks. Do this during setUp instead of setUpClass
        so that each test has access to a clean list of mocks.

        '''
        self.mock_hookenv_status()

    def tearDown(self):
        for patcher in self._patchers:
            patcher.stop()

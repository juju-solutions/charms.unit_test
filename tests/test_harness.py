import unittest
from charms.unit import Harness

with Harness.patch_imports('charms_mock.layer.foo'):
    import haslayerdir

with Harness.patch_imports('charms_other_mock', 'charms_other_mock.layer.bar'):
    import nolayerdir


class TestHasLayerDir(Harness):

    def test_has_layer_dir(self):
        '''
        Test to verify that we can mock out imports

        '''
        # Verify that our import is usable.
        test_class = haslayerdir.HasLayerDir()

        self.assertEqual(test_class.test(), 'test has layer dir!')

        # Verify that we can make calls to mocked out methods
        self.assertTrue(test_class.foo_lives())

        # Verify that we haven't mocked out stuff that actually exists.
        test_class = haslayerdir.HasLayerDirLib()

        self.assertEqual(test_class.test(), 'test has layer dir lib!')

class TestNoLayerDir(Harness):

    def test_no_layer_dir(self):

        # Verify that our import is usable
        test_class = nolayerdir.NoLayerDir()

        self.assertEqual(test_class.test(), 'test has no layer dir!')

        # Verif that we can call mocked out stuff

        self.assertTrue(test_class.bar_lives())

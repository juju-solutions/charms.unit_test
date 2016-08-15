import unittest
from charms.unit import Harness
import os
import mock
import sys

with Harness.patch_imports('charms_mock', 'charms_mock.layer.bar'):
    from reactive import nolayerdir


class TestNoLayerDir(Harness):

    def test_no_layer_dir(self):

        # Verify that our import is usable
        test_class = nolayerdir.NoLayerDir()
        self.assertEqual(test_class.test(), 'test has no layer dir!')

        # Verif that we can call mocked out stuff
        self.assertTrue(test_class.bar_lives())

        # Verify that we can make calls to mocked out options
        self.assertTrue(test_class.options_mocked())


if __name__ == '__main__':
    unittest.main()

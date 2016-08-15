import unittest
from charms.unit import Harness
import os
import mock
import sys

from reactive import haslayerdir


class TestHasLayerDir(Harness):

    def setUp(self):
        self.search_dirs.append('lib/charms_mock/layer')
        super(TestHasLayerDir, self).setUp()

    def test_has_layer_dir(self):
        # Verify that our import is usable.
        test_class = haslayerdir.HasLayerDir()
        self.assertEqual(test_class.test(), 'test has layer dir!')

        # Verify that we can make calls to mocked out options
        self.assertTrue(test_class.options_mocked())

        # Verify that we haven't mocked out stuff that actually exists.
        self.assertTrue(test_class.has_layer_dir_lib())

if __name__ == '__main__':
    unitttest.main()


from charms_mock import layer
from charms_mock.layer.haslayerdir import HasLayerDirLib

class HasLayerDir(object):

    def test(self):
        return "test has layer dir!"

    def foo_lives(self):
        layer.foo()
        return True

    def has_layer_dir_lib(self):
        lib = HasLayerDirLib()
        return True

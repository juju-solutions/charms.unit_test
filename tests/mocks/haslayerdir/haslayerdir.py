from charms_mock import layer

class HasLayerDir(object):

    def test(self):
        return "test has layer dir!"

    def foo_lives(self):
        layer.foo()
        return True

HasLayerDirLib = layer.haslayerdir

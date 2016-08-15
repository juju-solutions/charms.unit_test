from charms_mock import layer
from charms_mock.layer.bar import Bar

class NoLayerDir(object):

    def test(self):
        return "test has no layer dir!"

    def options_mocked(self):
        layer.options()
        return True

    def bar_lives(self):
        Bar()
        return True

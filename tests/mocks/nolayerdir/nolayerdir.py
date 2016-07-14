from charms_other_mock.layer.bar import Bar
from charms_other_mock import layer

class NoLayerDir(object):

    def test(self):
        return "test has no layer dir!"

    def bar_lives(self):
        Bar()
        return True

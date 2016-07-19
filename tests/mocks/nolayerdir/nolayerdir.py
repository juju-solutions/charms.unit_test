from charms_other_mock.layer.bar import Bar

class NoLayerDir(object):

    def test(self):
        return "test has no layer dir!"

    def bar_lives(self):
        Bar()
        return True

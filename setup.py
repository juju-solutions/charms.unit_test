from distutils.core import setup
import os


version_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'VERSION'))
with open(version_file) as v:
    VERSION = v.read().strip()


SETUP = {
    'name': "charms.unit",
    'version': VERSION,
    'author': "Ubuntu Developers",
    'author_email': "ubuntu-devel-discuss@lists.ubuntu.com",
    'url': "https://github.com/juju-solutions/charms.unit",
    'packages': [
        "charms",
        "charms.unit",
    ],
    'install_requires': [
        'mock',
    ],
    'scripts': [],
    'license': "Apache License 2.0",
    'long_description': open('README.md').read(),
    'description': 'Framework for unit testing Juju Charms',
}

if __name__ == '__main__':
    setup(**SETUP)

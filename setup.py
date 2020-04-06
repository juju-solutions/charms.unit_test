from setuptools import setup


SETUP = {
    'name': "charms.unit_test",
    'version': '1.0.0',
    'author': "Cory Johns",
    'author_email': "johnsca@gmail.com",
    'url': "https://github.com/juju-solutions/charms.unit_test",
    'packages': [
        "charms",
    ],
    'install_requires': [
    ],
    'license': "Apache License 2.0",
    'long_description': open('README.md').read(),
    'description': 'Helpers for unit-testing reactive-style Juju Charms',
}


if __name__ == '__main__':
    setup(**SETUP)

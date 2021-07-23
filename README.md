# charms.unit\_test

This library provides helpers for unit testing reactive style charms,
layers, and interfaces.


## Usage

This library is intended to be used with pytest and `conftest.py`, which
allows for mocking out imports prior to the test code being loaded.

Example `conftest.py`:

```python
from charms.unit_test import patch_reactive, patch_module

# patch common things needed by any reactive charm
patch_reactive()

# patch some other module that the charm expects to be there
patch_module('charms.leadership')
```

With this, your test code can import the charm's reactive code which
depends on charms.reactive and charmhelpers without error, and the
libraries will be mocked out so that you can call your handlers
directly to test them.


## Reference

More details on what is patched, as well as what other helpers are available,
can be found in [the reference docs](docs/reference.md).

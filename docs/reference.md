# Reference

## `patch_reactive()`

Setup the standard patches that any reactive charm will require.

In addition to patching the `charms.reactive` library and all of its dependencies (such
as `charmhelpers`), it also installs mocks and helpers for the following:

  * **`charms.layer.*`** Layer libraries which are not already available (i.e., provided
    by the charm or layer) are automatically patched, so that the charm or layer does
    not need to be built to run unit tests.

  * **`@when_*()`, `@hook()`, `@atexit`, etc.** Standard decorators are patched with
    pass-through decorators so that handler functions can be tested directly.

  * **`set_flag()`, `clear_flag()`, `is_flag_set()`, etc.** Flag functions are patched
    to work with in-memory data, so they can be set, cleared, and tested just as they
    would be in the charm.

  * **`charmhelpers.core.unitdata.kv()`** UnitData is patched to work with in-memory
    data so that it can be written and read just as it would be in the charm.

  * **`Endpoint`** The base class for interfaces is patched so that interface layers can
    be tested as you would expect. When creating an instance of an `Endpoint` subclass,
    in addition to the endpoint name, you can pass in a list of relation ID values which
    will then pre-populate the set of relations with mock relations that have empty
    dicts for the relation data fields (`to_publish`, `to_publish_raw`, `received`, and
    `received_raw`). Unlike real relation instances, though, the raw and non-raw data
    are entirely independent.


## `patch_module(fullname, replacement=None)`

This patches the given named module, along with any parent package which is not already
available. If `replacement` is given, that is used instead of a new `MagicMock`.

This gets around a few gotchas that can come up when patching modules themselves using
`unittest.mock.patch()`, and ensures that any subsequent import that tries to load that
module or any of it's parent packages will succeed and get the patched version.

This is easier and more descriptive to use in `conftest.py` to ensure that you can
import your charm code at the top of your test and have any modules that it imports
already be available and patched. It can also be used as a context manager; this can be
used to temporarily replace an existing module, such as one provided by your charm or
layer, in order to test other functionality.


## `patch_fixture(patch_target, new=None, patch_opts=None, fixture_opts=None)`

Create a pytest fixture which patches the target when used by a test case.

The `patch_opts` param can be used to pass keyword arguments to `unittest.mock.patch()`
and the `new` param is a shortcut for `patch_opts={'new': new}`.

Equivalently, `fixture_opts` can be used to pass to keyword arguments to the
`@pytest.fixture()` decorator.


## `identity(x, *args, **kwargs)`

A helper function that just returns `x` unchanged. This is mostly used to turn
decorators into no-ops which leave the decorated function entirely unchanged, but it may
be useful to replace some other functions as well.


## `flags`

This is the in-memory `set()` which the patched flag functions (`set_flag()`,
`clear_flag()`, `is_flag_set()`, etc.) use. Generally, you would just access it through
those functions, but if you need to set or check for a large number of flags at once, or
if you want to clear the set of flags between tests, it might be cleaner to access it
directly.

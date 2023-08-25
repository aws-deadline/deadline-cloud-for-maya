By default, this package is configured to run PyTest tests
(http://pytest.org/).

## Writing tests

Place test files in this directory, using file names that start with `test_`.

## Running tests

To run the full suite against all interpreters, run:
```
$ ./build.sh test [<tox_arguments>]
```

By default, the package is set up to automatically pass any unknown flags forwards to pytest.  Check the tox and pytest documentation for more information.

Code coverage is automatically reported for ;
to add other packages, modify `pyproject.toml` in the package root directory.

To debug failing tests, use the helpful `guard` command which runs the testing on a watch looponfailroots

```
$ ./build.sh guard
```

Or if you want to debug the tests with a debugger open to the failed test, use pytest's pdb option:
```
$ ./build.sh pytest --pdb
```

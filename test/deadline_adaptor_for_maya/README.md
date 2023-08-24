By default, this package is configured to run PyTest tests
(http://pytest.org/).

## Writing tests

Place test files in this directory, using file names that start with `test_`.

## Running tests

```
$ ./build.sh test
```

To configure pytest's behaviour in a single run, you can add options using the --addopts flag:

```
$ ./build.sh test --addopts="[pytest options]"
```

For example, to run a single test, or a subset of tests, you can use pytest's
options to select tests:

```
$ ./build.sh test --addopts="-k TEST_PATTERN"
```

Code coverage is automatically reported for deadline_worker_maya_adaptor;
to add other packages, modify setup.cfg in the package root directory.

To debug the failing tests:

```
$ ./build.sh test --addopts=--pdb
```

This will drop you into the Python debugger on the failed test.

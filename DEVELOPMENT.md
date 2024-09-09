# Development documentation

This package has two active branches:

- `mainline` -- For active development. This branch is not intended to be consumed by other packages. Any commit to this branch may break APIs, dependencies, and so on, and thus break any consumer without notice.
- `release` -- The official release of the package intended for consumers. Any breaking releases will be accompanied with an increase to this package's interface version.

## Build / Test / Release

### Build the package

```bash
hatch build
```

### Run tests

```bash
hatch run test
```

### Run linting

```bash
hatch run lint
```

### Run formatting

```bash
hatch run fmt
```

### Run tests for all supported Python versions

```bash
hatch run all:test
```

## Use development Submitter in Maya

```bash
hatch run install
hatch shell
```
Then launch Maya from that terminal.

A development version of deadline-cloud-for-maya is then available to be loaded.

## Submitter Development Workflow

WARNING: This workflow installs additional Python packages into your Maya's python distribution.

1. Create a development location within which to do your git checkouts. For example `~/deadline-clients`. Clone packages from this directory with commands like `git clone git@github.com:casillas2/deadline-cloud-for-maya.git`. You'll also want the `deadline-cloud` and `openjd` repos.
2. Switch to your Maya directory, like `cd "C:\Program Files\Autodesk\Maya2024"`.
3. Run `.\mayapy -m pip install -e C:\Users\<username>\deadline-clients\deadline-cloud` to install the AWS Deadline Cloud Client Library in edit mode.
4. Run `.\mayapy -m pip install -e C:\Users\<username>\deadline-clients\openjd-adaptor-runtime-for-python` to install the Open Job Description Adaptor Runtime Library in edit mode.
5. Run `.\mayapy -m pip install -e C:\Users\<username>\deadline-clients\deadline-cloud-for-maya` to install the Maya submitter in edit mode.
6. Edit (create if missing) your `~/Documents/maya/2024/Maya.env` file, and add the following lines to it:

   ```bash
   DEADLINE_ENABLE_DEVELOPER_OPTIONS=true
   MAYA_MODULE_PATH=C:\Users\<username>\deadline-clients\deadline-cloud-for-maya\maya_submitter_plugin
   ```

   The developer options add a shelf TEST button you can use to run the tests from the `job_bundle_output_tests` directory.
7. Run Maya. Go to Windows > Settings/Preferences > Plug-In Manager and you will find that `DeadlineCloudForMaya.py` is available as a plugin. Check the checkbox to have Maya load the plugin and create the Deadline tray for you. Click the icon on the tray to open the submitter.

## Application Interface Adaptor Development Workflow

You can work on the adaptor alongside your submitter development workflow using a Deadline Cloud
farm that uses a service-managed fleet. You'll need to perform the following steps to substitute
your build of the adaptor for the one in the service.

1. Use the development location from the Submitter Development Workflow. Make sure you're running Maya with `set DEADLINE_ENABLE_DEVELOPER_OPTIONS=true` enabled.
2. Build wheels for `openjd_adaptor_runtime`, `deadline` and `deadline_cloud_for_maya`, place them in a "wheels" folder in `deadline-cloud-for-maya`. A script is provided to do this, just execute from `deadline-cloud-for-maya`:

   ```bash
   # If you don't have the build package installed already
   $ pip install build
   ...
   $ ./scripts/build_wheels.sh
   ```

   Wheels should have been generated in the "wheels" folder:

   ```bash
   $ ls ./wheels
   deadline_cloud_for_maya-<version>-py3-none-any.whl
   deadline-<version>-py3-none-any.whl
   openjd_adaptor_runtime-<version>-py3-none-any.whl
   ```

3. Open the Maya integrated submitter, and in the Job-Specific Settings tab, enable the option 'Include Adaptor Wheels'. This option is only visible when the environment variable `DEADLINE_ENABLE_DEVELOPER_OPTIONS` is set to `true`. Then submit your test job.



NOTE: The MayaAdaptor expects that the MayaPY executable is named `mayapy` and is set on the PATH. If this is not the case, you can set the `MAYA_ADAPTOR_MAYAPY_EXECUTABLE` environment variable to the path to the MayaPy executable.

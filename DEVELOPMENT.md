# Development documentation

This documentation provides guidance on developer workflows for working with the code in this repository.

Table of Contents:

* [Development Environment Setup](#development-environment-setup)
* [The Development Loop](#the-development-loop)
   * [Submitter Development Workflow](#submitter-development-workflow)
      * [Running the Plug-In](#running-the-plug-in)
      * [Making Code Changes](#making-submitter-code-changes)
      * [Running Tests](#running-submitter-tests)
   * [Adaptor Development Workflow](#adaptor-development-workflow)
      * [Running the Adaptor Locally](#running-the-adaptor-locally)
      * [Running the Adaptor on a Farm](#running-the-adaptor-on-a-farm)
      * [Testing the Adaptor](#testing-the-adaptor)

## Development Environment Setup

To develop the Python code in this repository you will need:

1. Python 3.9 or higher. We recommend [mise](https://github.com/jdx/mise) if you would like to run more than one version
   of Python on the same system. When running unit tests against all supported Python versions, for instance.
2. The [hatch](https://github.com/pypa/hatch) package installed (`pip install --upgrade hatch`) into your Python environment.
3. An install of a supported version of Maya.
4. A valid AWS Account.
5. An AWS Deadline Cloud Farm to run jobs on. We recommend following the quickstart in the Deadline Cloud console to create a
   Queue with the default Queue Environment, and a Service Managed Fleet.

You can develop on a Linux, MacOS, or Windows workstation.

## Software Architecture

If you are not already familiar with the architecture of the Maya submitter plugin and adaptor application in this repository
then we suggest going over the [software architecture](docs/software_arch.md) for an overview of the components and how they function.

## The Development Loop

We have configured [hatch](https://github.com/pypa/hatch) commands to support a standard development loop. You can run the following
from any directory of this repository:

* `hatch build` - To build the installable Python wheel and sdist packages into the `dist/` directory.
* `hatch run test` - To run the PyTest unit tests found in the `test/unit` directory. See [Testing](#testing).
* `hatch run all:test` - To run the PyTest unit tests against all available supported versions of Python.
* `hatch run lint` - To check that the package's formatting adheres to our standards.
* `hatch run fmt` - To automatically reformat all code to adhere to our formatting standards.
* `hatch shell` - Enter a shell environment that will have Python set up to import your development version of this package.
* `hatch env prune` - Delete all of your isolated workspace [environments](https://hatch.pypa.io/1.12/environment/)
   for this package.
* `hatch run install` - Install the DeadlineCloudForMaya plugin from this repository into a temporary directory within this repository.

Note: Hatch uses [environments](https://hatch.pypa.io/1.12/environment/) to isolate the Python development workspace
for this package from your system or virtual environment Python. If your build/test run is not making sense, then
sometimes pruning (`hatch env prune`) all of these environments for the package can fix the issue.

### Submitter Development Workflow

The submitter plug-in generates job bundles to submit to AWS Deadline Cloud. Developing a change
to the submitter involves iteratively changing the plug-in code, then running the plug-in within Maya
to generate or submit a job bundle, inspecting the generated job bundle to ensure that it is as you expect,
and ultimately running that job to ensure that it works as desired.

#### Running the Plug-In

First, create a development installation of the submitter plug-in by running:

```bash
hatch run install
```

This will create a `/plugin_env` directory in this repository with the submitter plug-in and all of its
dependencies installed into it. Then, activate the hatch shell environment, set the environment variable to enable
developer options in the plugin, and run maya:

```bash
hatch shell
export DEADLINE_ENABLE_DEVELOPER_OPTIONS=true
maya
```

You will need to load the plug-in within Maya once the application has completed loading. In the main menu bar, go to
Windows > Settings/Preferences > Plug-In Manager and you will find that `DeadlineCloudForMaya.py` is available as a
plug-in. Check the checkbox to have Maya load the plug-in and create the AWSDeadline tray for you. Click the icon on
the tray to open the submitter.

You can use the "Export Bundle" option in the submitter to save the job bundle for a submission to your local disk
to inspect it, or the "Submit" button (after selecting your Deadline Cloud Farm and Queue in the submitter UI) to
submit the job to your farm to run.

#### Making Submitter Code Changes

Whenever you modify code for the plug-in, or one of its supporting Python libraries, you will need to re-run
the `hatch run install` to repackage the changes, and then uncheck then check the option to load the plug-in in
Maya's Plug-In Manager; if you do not reload the plug-in in Maya, then your changes will not take effect.

#### Running Submitter Tests

The tests for the plug-in have two forms:

1. Unit tests - Small tests that are narrowly focused on ensuring that function-level behavior of the
   implementation behaves as it is expected to. These can always be run locally on your workstation without
   requiring an AWS account.
2. Integration tests - In-application tests that verify that job submissions generate expected job bundles.

##### Unit Tests

Unit tests are all located under the `test/deadline_submitter_for_maya/unit` directory of this repository. If you are adding
or modifying functionality, then you will almost always want to be writing one or more unit tests to demonstrate that your
logic behaves as expected and that future changes do not accidentally break your change.

To run the unit tests, simply use hatch:

```bash
hatch run test
```

##### Integration Tests

Integration tests are built in to the plug-in itself. They are available as the `TEST` button in the AWSDeadline
shelf when you run Maya with the environment variable `DEADLINE_ENABLE_DEVELOPER_OPTIONS=true`. If you are adding
or modifying functionality that will affect the content of a generated job bundle then you will likely want to
be writing or modifying an integration test for your change.

To run the integration tests:
1. Select the `TEST` button from the AWSDeadline shelf; and then
2. Select the `/job_bundle_output_tests` directory within this repository.

The test results will be saved to a file called `test-job-bundle-results.txt` within the test directory
that you selected.

### Adaptor Development Workflow

The maya adaptor is a command-line application (named `maya-openjd`) that interfaces with the Maya application.
You will need the `maya` executable available in your PATH for the adaptor to be able to run Maya.

When developing a change to the Maya adaptor we recommend primarily running the adaptor locally on your workstation,
and running and adding to the unit tests until you are comfortable that your change looks like it is working as you expect.
Testing locally like this will allow you to iterate faster on your change than the alternative of testing by
submitting jobs to Deadline Cloud to run using your modified adaptor. Then, test it out on a real render farm only once
you think that your change is functioning as you'd like.

#### Running the Adaptor Locally

To run the adaptor you will first need to create two files:

1. An `init-data.yaml` (or `init-data.json`) file that contains the information passed to the adaptor
   during its initialization phase. The schema for this file can be found at
   `src/deadline/maya_adaptor/MayaAdaptor/schemas/init_data.schema.json`, and examples of init data can
   be found in the `template.yaml` files spread throughout this repository.
2. A `run-data.yaml` (or `run-data.json`) file that contains the information passed to the adaptor
   to do a single Task run. The schema for this file can be found at
   `src/deadline/maya_adaptor/MayaAdaptor/schemas/run_data.schema.json`, and examples of run data can
   be found in the `template.yaml` files spread throughout this repository.

To run the adaptor once you have created an `init-data.yaml` and `run-data.yaml` file to test with:

1. Ensure that `maya` can be run directly in your terminal by putting its location in your PATH environment variable.
2. Enter the hatch shell development environment by running `hatch shell`
3. Run the `maya-openjd` commmand-line with arguments that exercise your code change.

The adaptor has two modes of operation:

1. Running directly via the `maya-openjd run` subcommand; or
2. Running as a background daemon via subcommands of the `maya-openjd daemon` subcommand.

We recommend primarily developing using the `maya-openjd run` subcommand as it is simpler to operate
for rapid development iterations, but that you should also ensure that your change works with the background
daemon mode with multiple `run` commands before calling your change complete.

The basic command to run the `maya-openjd` run command will look like:

```bash
maya-openjd run \
  --init-data file://<absolute-path-to-init-data.yaml> \
  --run-data file://<absolute-path-to-run-data.yaml>
```

The equivalent run with the `maya-openjd daemon` subcommand looks like:

```bash
# The daemon start command requires that the connection-info file not already exist.
test -f connection-info.json || rm connection-info.json

# This starts up a background process running the adaptor, and runs the `on_init` and `on_start`
# methods of the adaptor.
maya-openjd daemon start \
  --init-data file://<absolute-path-to-init-data.yaml> \
  --connection-file file://connection-info.json

# This connects to the already running adaptor, via the information in the connection-info.json file,
# and runs the adaptor's `on_run` method.
# When testing, we suggest doing multiple "daemon run" commands with different inputs before
# running "daemon stop". This will help identify problems caused by data carrying over from a previous
# run.
maya-openjd daemon run \
  --run-data file://<absolute-path-to-run-data.yaml> \
  --connection-file file://connection-info.json

# This connects to the already running adaptor to instruct it to shutdown the maya application
# and then exit.
maya-openjd daemon stop \
  --connection-file file://connection-info.json
```

#### Running the Adaptor on a Farm

If you have made modifications to the adaptor and wish to test your modifications on a live Deadline Cloud Farm
with real jobs, then we recommend using a [Service Managed Fleet](https://docs.aws.amazon.com/deadline-cloud/latest/userguide/smf-manage.html)
for your testing. We recommend performing this style of test if you have made any modifications that might interact with Deadline Cloud's
job attachments feature, or that could interact with path mapping in any way. We have implemented a developer feature in the Maya submitter
plug-in that submits the Python wheel files for your modified adaptor along with your job submission and uses the modified adaptor to
run the submitted job.

You'll need to perform the following steps to substitute your build of the adaptor for the one in the service.

1. Using the submitter development workflow (See [Running the Plug-In](#running-the-plug-in)), make sure that you are
   running Maya with `DEADLINE_ENABLE_DEVELOPER_OPTIONS=true` enabled.
2. Clone the [deadline-cloud](https://github.com/aws-deadline/deadline-cloud) and
   [openjd-adaptor-runtime-for-python](https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python) repositories beside
   this one, and ensure that you `git checkout release` in each to checkout the latest `release` branch.
2. Build wheels for `openjd_adaptor_runtime`, `deadline` and `deadline_cloud_for_maya`, place them in a "wheels" folder in `deadline-cloud-for-maya`.
   A script is provided to do this, just execute from `deadline-cloud-for-maya`:

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

#### Testing the Adaptor

Unit tests are all located under the `test/deadline_submitter_for_maya/unit` directory of this repository. If you are adding
or modifying functionality, then you will almost always want to be writing one or more unit tests to demonstrate that your
logic behaves as expected and that future changes do not accidentally break your change.

To run the unit tests, simply use hatch:

```bash
hatch run test
```

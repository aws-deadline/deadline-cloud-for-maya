# AWS Deadline Cloud for Maya

[![pypi](https://img.shields.io/pypi/v/deadline-cloud-for-maya.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-maya)
[![python](https://img.shields.io/pypi/pyversions/deadline-cloud-for-maya.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-maya)
[![license](https://img.shields.io/pypi/l/deadline-cloud-for-maya.svg?style=flat)](https://github.com/aws-deadline/deadline-cloud-for-maya/blob/mainline/LICENSE)

AWS Deadline Cloud for Maya is a Python package that supports creating and running Audodesk Maya jobs within [AWS Deadline Cloud][deadline-cloud].
It provides both the implementation of a Maya plug-in for your workstation that helps you offload the computation for your rendering workloads
to [AWS Deadline Cloud][deadline-cloud] to free up your workstation's compute for other tasks, and the implementation of a command-line
adaptor application based on the [Open Job Description (OpenJD) Adaptor Runtime][openjd-adaptor-runtime] that improves AWS Deadline Cloud's
ability to run Maya efficiently on your render farm.

[deadline-cloud]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/what-is-deadline-cloud.html
[deadline-cloud-client]: https://github.com/aws-deadline/deadline-cloud
[openjd]: https://github.com/OpenJobDescription/openjd-specifications/wiki
[openjd-adaptor-runtime]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python
[openjd-adaptor-runtime-lifecycle]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python/blob/release/README.md#adaptor-lifecycle
[service-managed-fleets]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/smf-manage.html
[default-queue-environment]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/create-queue-environment.html#conda-queue-environment

## Compatibility

This library requires:

1. Maya 2023 - 2024,
1. Python 3.9 or higher; and
1. Linux, Windows, or a macOS operating system.

## Versioning

This package's version follows [Semantic Versioning 2.0](https://semver.org/), but is still considered to be in its 
initial development, thus backwards incompatible versions are denoted by minor version bumps. To help illustrate how
versions will increment during this initial development stage, they are described below:

1. The MAJOR version is currently 0, indicating initial development. 
2. The MINOR version is currently incremented when backwards incompatible changes are introduced to the public API. 
3. The PATCH version is currently incremented when bug fixes or backwards compatible changes are introduced to the public API. 

## Getting Started

This Maya integration for AWS Deadline Cloud has two components that you will need to install:

1. The Maya submitter plug-in must be installed on the workstation that you will use to submit jobs; and
2. The Maya adaptor must be installed on all of your AWS Deadline Cloud worker hosts that will be running the Maya jobs that you submit.

Before submitting any large, complex, or otherwise compute-heavy Maya render jobs to your farm using the submitter and adaptor that you
set up, we strongly recommend that you construct a simple test scene that can be rendered quickly and submit renders of that
scene to your farm to ensure that your setup is correctly functioning.

### Maya Submitter Plug-in

The Maya submitter plug-in creates a shelf button in your Maya UI that can be used to submit jobs to AWS Deadline Cloud. Clicking this button
reveals a UI to create a job submission for AWS Deadline Cloud using the [AWS Deadline Cloud client library][deadline-cloud-client].
It automatically determines the files required based on the loaded scene, allows the user to specify render options, builds an
[Open Job Description template][openjd] that defines the workflow, and submits the job to the farm and queue of your chosing.

To install the submitter plug-in:

1. Install the `deadline-cloud-for-maya` Python package, with `mayapy`, into the Maya installation on your workstation by following 
   Maya's official online documentation (e.g. [For Maya 2024][maya-2024-mayapy]).
2. Copy the contents of the 
   [`/maya_submitter_plugin` directory](https://github.com/aws-deadline/deadline-cloud-for-maya/tree/release/maya_submitter_plugin)
   from the release branch of [deadline-cloud-for-maya GitHub repository](https://github.com/aws-deadline/deadline-cloud-for-maya) into
   a directory in Maya's module search paths. See the `MAYA_MODULE_PATH` section of Maya's official documentation 
   (e.g. [For Maya 2024][maya-2024-module-path]) for a list of the default search paths on your system.
3. Within Maya, enable the DealineCloudForMaya plug-in in Maya's Plug-in Manager.
   (Main menu bar: Windows -> Settings/Preferences -> Plug-in Manager)
4. To supply AWS account credentials for the submitter to use when submitting a job you can either:
    1. [Install and set up the Deadline Cloud Monitor][deadline-cloud-monitor-setup], and then log in to the monitor. Logging in
       to the monitor will make AWS credentials available to the submitter, automatically.
    2. Set up an AWS credentials profile [as you would for the AWS CLI][aws-cli-credentials], and select that profile for the submitter
       to use.
    3. Or default to your AWS EC2 instance profile credentials if you are running a workstation in the cloud.

[maya-2024-mayapy]: https://help.autodesk.com/view/MAYAUL/2024/ENU/?guid=GUID-72A245EC-CDB4-46AB-BEE0-4BBBF9791627
[maya-2024-module-path]: https://help.autodesk.com/view/MAYAUL/2024/ENU/?guid=GUID-228CCA33-4AFE-4380-8C3D-18D23F7EAC72
[deadline-cloud-monitor-setup]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/submitter.html#install-deadline-cloud-monitor
[aws-cli-credentials]: https://docs.aws.amazon.com/cli/v1/userguide/cli-chap-authentication.html

### Maya Adaptor

Jobs created by this submitter require this adaptor be installed on your worker hosts, and that both the installed adaptor
and the Maya executable be available on the PATH of the user that will be running your jobs.

The adaptor application is a command-line Python-based application that enhances the functionality of Maya for running
within a render farm like Deadline Cloud. Its primary purpose for existing is to add a "sticky rendering" functionality
where a single process instance of Maya is able to load the scene file and then dynamically be instructed to perform
desired renders without needing to close and re-launch Maya between them. It also has additional benefits
such as support for path mapping, and reporting the progress of your render to Deadline Cloud. The alternative 
to "sticky rendering" is that Maya would need to be run separately for each render that is done, and close afterwards.
Some scenes can take 10's of minutes just to load for rendering, so being able to keep the application open and loaded between
renders can be a significant time-saving optimization; particularly when the render itself is quick.

If you are using the [default Queue Environment][default-queue-environment], or an equivalent, to run your jobs, then the adaptor will be
automatically made available to your job. Otherwise, you will need to install the adaptor.

The adaptor can be installed by the standard python packaging mechanisms:
```sh
$ pip install deadline-cloud-for-maya
```

After installation, test that it has been installed properly by running the following as the same user that runs your jobs and
that `maya` can be run as the same user:
```sh
$ maya-openjd --help
$ maya -help
```

For more information on the commands the OpenJD adaptor runtime provides, see [here][openjd-adaptor-runtime-lifecycle].

### Maya Software Availability in AWS Deadline Cloud Service Managed Fleets

You will need to ensure that the version of Maya that you want to run is available on the worker host when you are using
AWS Deadline Cloud's [Service Managed Fleets][service-managed-fleets] to run jobs;
hosts do not have any rendering applications pre-installed. The standard way of accomplishing this is described
[in the service documentation](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/provide-applications.html).
You can find a list of the versions of Maya that are available by default 
[in the user guide](https://docs.aws.amazon.com/deadline-cloud/latest/userguide/create-queue-environment.html#conda-queue-environment)
if you are using the default Conda queue enivonment in your setup.

## Viewing the Job Bundle that will be submitted

To submit a job, the submitter first generates a [Job Bundle][job-bundle], and then uses functionality from the
[Deadline][deadline-cloud-client] package to submit the Job Bundle to your render farm to run. If you would like to see
the job that will be submitted to your farm, then you can use the "Export Bundle" button in the submitter to export the
Job Bundle to a location of your choice. If you want to submit the job from the export, rather than through the
submitter plug-in then you can use the [Deadline Cloud application][deadline-cloud-client] to submit that bundle to your farm.

[job-bundle]: https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/build-job-bundle.html

## Security

We take all security reports seriously. When we receive such reports, we will 
investigate and subsequently address any potential vulnerabilities as quickly 
as possible. If you discover a potential security issue in this project, please 
notify AWS/Amazon Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/)
or directly via email to [AWS Security](aws-security@amazon.com). Please do not 
create a public GitHub issue in this project.

## Telemetry

See [telemetry](https://github.com/aws-deadline/deadline-cloud-for-maya/blob/release/docs/telemetry.md) for more information.

## License

This project is licensed under the Apache-2.0 License.

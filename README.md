[![pypi](https://img.shields.io/pypi/v/deadline-cloud-for-maya.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-maya)
[![python](https://img.shields.io/pypi/pyversions/deadline-cloud-for-maya.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-maya)
[![license](https://img.shields.io/pypi/l/deadline-cloud-for-maya.svg?style=flat)](https://github.com/aws-deadline/deadline-cloud-for-maya/blob/mainline/LICENSE)

# AWS Deadline Cloud for Maya

AWS Deadline Cloud for Maya is a python package that allows users to create [AWS Deadline Cloud][deadline-cloud] jobs from within Maya. Using the [Open Job Description (OpenJD) Adaptor Runtime][openjd-adaptor-runtime] this package also provides a command line application that adapts Maya's command line interface to support the [OpenJD specification][openjd].

[deadline-cloud]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/what-is-deadline-cloud.html
[deadline-cloud-client]: https://github.com/aws-deadline/deadline-cloud
[openjd]: https://github.com/OpenJobDescription/openjd-specifications/wiki
[openjd-adaptor-runtime]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python
[openjd-adaptor-runtime-lifecycle]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python/blob/release/README.md#adaptor-lifecycle

## Compatibility

This library requires:

1. Maya 2023 - 2024,
1. Python 3.9 or higher; and
1. Linux, Windows, or a macOS operating system.

## Submitter

This package provides a Maya plugin that creates jobs for AWS Deadline Cloud using the [AWS Deadline Cloud client library][deadline-cloud-client]. Based on the loaded scene it determines the files required, allows the user to specify render options, and builds an [OpenJD template][openjd] that defines the workflow.

## Adaptor

The Maya Adaptor implements the [OpenJD][openjd-adaptor-runtime] interface that allows render workloads to launch Maya and feed it commands. This gives the following benefits:
* a standardized render application interface,
* sticky rendering, where the application stays open between tasks,
* path mapping, that enables cross-platform rendering

Jobs created by the submitter use this adaptor by default.

### Getting Started

The adaptor can be installed by the standard python packaging mechanisms:
```sh
$ pip install deadline-cloud-for-maya
```

After installation it can then be used as a command line tool:
```sh
$ maya-openjd --help
```

For more information on the commands the OpenJD adaptor runtime provides, see [here][openjd-adaptor-runtime-lifecycle].

## Versioning

This package's version follows [Semantic Versioning 2.0](https://semver.org/), but is still considered to be in its 
initial development, thus backwards incompatible versions are denoted by minor version bumps. To help illustrate how
versions will increment during this initial development stage, they are described below:

1. The MAJOR version is currently 0, indicating initial development. 
2. The MINOR version is currently incremented when backwards incompatible changes are introduced to the public API. 
3. The PATCH version is currently incremented when bug fixes or backwards compatible changes are introduced to the public API. 

## Security

See [CONTRIBUTING](https://github.com/aws-deadline/deadline-cloud-for-maya/blob/release/CONTRIBUTING.md#security-issue-notifications) for more information.

## Telemetry

See [telemetry](https://github.com/aws-deadline/deadline-cloud-for-maya/blob/release/docs/telemetry.md) for more information.

## License

This project is licensed under the Apache-2.0 License.

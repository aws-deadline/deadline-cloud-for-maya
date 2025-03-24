#!/bin/bash

# This script is called in a shell subprocess.
# If editing this script, please see the security considerations
# of this invocation method:
# https://docs.python.org/3/library/subprocess.html#security-considerations

set -xeuo pipefail

python depsBundle.py

rm -f dependency_bundle/deadline_cloud_for_maya_submitter-deps-windows.zip
rm -f dependency_bundle/deadline_cloud_for_maya_submitter-deps-linux.zip
rm -f dependency_bundle/deadline_cloud_for_maya_submitter-deps-macos.zip

cp dependency_bundle/deadline_cloud_for_maya_submitter-deps.zip dependency_bundle/deadline_cloud_for_maya_submitter-deps-windows.zip
cp dependency_bundle/deadline_cloud_for_maya_submitter-deps.zip dependency_bundle/deadline_cloud_for_maya_submitter-deps-linux.zip
cp dependency_bundle/deadline_cloud_for_maya_submitter-deps.zip dependency_bundle/deadline_cloud_for_maya_submitter-deps-macos.zip

#!/bin/bash
set -xeuo pipefail

python depsBundle.py

rm -f dependency_bundle/deadline_submitter_for_maya-deps-windows.zip
rm -f dependency_bundle/deadline_submitter_for_maya-deps-linux.zip
rm -f dependency_bundle/deadline_submitter_for_maya-deps-macos.zip

cp dependency_bundle/deadline_submitter_for_maya-deps.zip dependency_bundle/deadline_submitter_for_maya-deps-windows.zip
cp dependency_bundle/deadline_submitter_for_maya-deps.zip dependency_bundle/deadline_submitter_for_maya-deps-linux.zip
cp dependency_bundle/deadline_submitter_for_maya-deps.zip dependency_bundle/deadline_submitter_for_maya-deps-macos.zip

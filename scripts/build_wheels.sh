#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

set -euo pipefail

if [ ! -d wheels ]; then
    mkdir wheels
fi
rm -f wheels/*

for dir in ../openjobio ../deadline-cloud ../deadline-cloud-for-maya; do
    echo "Building $dir..."
    python -m build --wheel --outdir ./wheels --skip-dependency-check $dir
done

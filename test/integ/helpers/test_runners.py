# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import subprocess
import yaml
import json

from pathlib import Path
from typing import Any


def run_command(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess[bytes]:
    try:
        output = subprocess.run(args, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        # Without this a hung adaptor prints nothing until the build itself times out,
        # since pytest only shows captured output once the test finishes.
        print(f"Timed out after {timeout}s: {' '.join(args)}")
        print(f"\nstdout:\n\n{(e.stdout or b'').decode('utf-8', errors='replace')}")
        print(f"\nstderr:\n\n{(e.stderr or b'').decode('utf-8', errors='replace')}")
        return subprocess.CompletedProcess(
            args, returncode=124, stdout=e.stdout or b"", stderr=e.stderr or b""
        )

    print(f"Ran the following: {' '.join(output.args)}")
    print(f"\nstdout:\n\n{output.stdout.decode('utf-8', errors='replace')}")
    print(f"\nstderr:\n\n{output.stderr.decode('utf-8', errors='replace')}")

    return output


def is_valid_template(template_location: Path) -> bool:
    output = run_command(
        ["mayapy", "-m", "openjd", "check", str(template_location), "--output", "json"]
    )

    output_json = json.loads(output.stdout)

    return output_json["status"] == "success"


def run_adaptor_test(template_path: Path, job_params: dict[str, Any]) -> None:
    with open(template_path) as f:
        template = yaml.safe_load(f)

    for step in template["steps"]:
        output = run_command(
            [
                "mayapy",
                "-m",
                "openjd",
                "run",
                str(template_path),
                "--step",
                step["name"],
                "--job-param",
                json.dumps(job_params),
            ]
        )
        assert output.returncode == 0

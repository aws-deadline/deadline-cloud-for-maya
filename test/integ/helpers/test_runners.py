# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import subprocess
import yaml
import json

from pathlib import Path
from typing import Any


def run_command(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    output = subprocess.run(args, capture_output=True)

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

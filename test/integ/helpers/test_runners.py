# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import subprocess
import tempfile
import yaml
import json

from pathlib import Path
from typing import Any


def run_command(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[bytes]:
    # Write to files rather than pipes. The adaptor backgrounds a daemon that inherits
    # our stdout/stderr, so with capture_output=True a timeout kills the child and then
    # blocks forever waiting for EOF from the surviving grandchild.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        timed_out = False
        try:
            returncode = subprocess.run(args, stdout=out, stderr=err, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            returncode = 124
        out.seek(0)
        err.seek(0)
        stdout, stderr = out.read(), err.read()

    if timed_out:
        print(f"Timed out after {timeout}s: {' '.join(args)}")
    else:
        print(f"Ran the following: {' '.join(args)}")
    print(f"\nstdout:\n\n{stdout.decode('utf-8', errors='replace')}")
    print(f"\nstderr:\n\n{stderr.decode('utf-8', errors='replace')}")

    return subprocess.CompletedProcess(args, returncode=returncode, stdout=stdout, stderr=stderr)


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


def run_native_reference(renderer: str, job_params: dict[str, Any], output_path: Path) -> Path:
    """Generate reference pixels using Maya directly, without importing the adaptor."""
    output_path.mkdir()
    request = {
        "renderer": renderer,
        "scene": job_params["MayaSceneFile"],
        "project": job_params["ProjectPath"],
        "output": str(output_path),
        "prefix": job_params["OutputFilePrefix"],
        "width": job_params["ImageWidth"],
        "height": job_params["ImageHeight"],
        "frame": int(job_params["Frames"]),
        "camera": "persp",
    }
    result = run_command(
        ["mayapy", str(Path(__file__).with_name("native_render.py")), json.dumps(request)]
    )
    assert result.returncode == 0, f"Native {renderer} reference render failed"
    # Maya can report a renderer error in its log while mayapy still exits zero.
    # A leftover/partial PNG must never turn an unlicensed render into a reference.
    render_log = (result.stdout + result.stderr).decode("utf-8", errors="replace").lower()
    assert (
        "rendering with watermarks" not in render_log
    ), f"Native {renderer} reference failed license authorization"
    assert "aborting render because" not in render_log, f"Native {renderer} reference aborted"
    assert any(output_path.glob("*.png")), f"Native {renderer} reference produced no PNG"
    return output_path

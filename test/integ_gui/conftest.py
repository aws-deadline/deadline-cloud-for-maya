# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Fixtures for the Maya submitter GUI tests. See README.md in this directory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pytest
from deadline_test_fixtures.deadline_mock import (
    MockDeadlineScenario,
    MockDeadlineServerProcess,
    write_deadline_config,
)

from ._launcher import (
    MayaSession,
    build_maya_environment,
    find_maya_executable,
    launch_maya_with_submitter,
    screenshot,
)
from ._pages import MayaSubmitterDialog


@pytest.fixture(scope="session")
def maya_executable() -> Path:
    try:
        return find_maya_executable()
    except FileNotFoundError as error:
        # Skip only when nothing asked for a specific Maya; a wrong path is an error.
        if os.environ.get("MAYA_EXECUTABLE"):
            pytest.fail(str(error))
        pytest.skip(str(error))


@pytest.fixture(scope="session")
def mock_deadline_server() -> Iterator[MockDeadlineServerProcess]:
    """The mock Deadline Cloud service, in its own process for the whole session.

    It runs out of process because xa11y's waits block the test process. Its queue
    has no job attachments, so Submit goes straight to CreateJob. Each response is
    delayed like the real service's, so races a zero-latency mock hides still show.
    """
    delay = float(os.environ.get("MOCK_DEADLINE_RESPONSE_DELAY_S", "0.3"))
    scenario = MockDeadlineScenario.without_job_attachments(response_delay_s=delay)
    with MockDeadlineServerProcess(scenario) as server:
        yield server


@dataclass
class SubmitterUnderTest:
    session: MayaSession
    dialog: MayaSubmitterDialog
    backend: object  # RemoteDeadlineBackend
    export_dir: Path


@pytest.fixture
def open_submitter(maya_executable, mock_deadline_server, tmp_path, request):
    """Return a function that launches Maya on a scene with the submitter open.

    Maya is stopped after the test. On failure, a screenshot and Maya's log are
    left in the test's tmp_path.
    """
    sessions: list[MayaSession] = []
    backend = mock_deadline_server.backend
    backend.reset()

    def _open(scene_file: Path) -> SubmitterUnderTest:
        config_path = tmp_path / "deadline.config"
        export_dir = tmp_path / "exported_bundles"
        export_dir.mkdir(exist_ok=True)
        write_deadline_config(
            config_path,
            farm_id=backend.farm_id,
            queue_id=backend.queue_id,
            job_history_dir=tmp_path / "job_history",
            job_bundle_default_directory=export_dir,
        )
        env = build_maya_environment(
            deadline_endpoint_url=mock_deadline_server.base_url,
            config_path=config_path,
            work_dir=tmp_path,
            scene_file=scene_file,
        )
        session = launch_maya_with_submitter(maya_executable, env, tmp_path)
        sessions.append(session)
        dialog = MayaSubmitterDialog.wait_for(session.process.pid)
        dialog.wait_settled()
        return SubmitterUnderTest(session, dialog, backend, export_dir)

    yield _open

    failed = getattr(request.node, "rep_call", None) is not None and request.node.rep_call.failed
    if failed:
        screenshot(tmp_path / "failure.png")
    for session in sessions:
        session.close()


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # Expose the call phase's result to fixtures, for the failure screenshot.
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        item.rep_call = report

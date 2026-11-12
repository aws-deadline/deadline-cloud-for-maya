# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Launch GUI Maya with the Deadline Cloud submitter open, for xa11y-driven tests.

Maya runs ``_opener.py`` at startup (``-command``), which opens the scene and the
submitter and reports through a status file. The submitter comes from the
developer install made by ``hatch run install`` (``plugin_env``, found through
``MAYA_ENV_DIR``), the same way a developer loads it.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from deadline_test_fixtures.deadline_mock import build_mock_environment

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ENV_DIR = REPO_ROOT / "plugin_env"
OPENER = Path(__file__).resolve().parent / "_opener.py"

# A cold GUI Maya start on a fresh runner, including the license checkout.
OPENER_TIMEOUT = 600.0

ENV_STATUS_FILE = "MAYA_SUBMITTER_UI_STATUS_FILE"
ENV_SCENE_FILE = "MAYA_SUBMITTER_UI_SCENE_FILE"

PRIVACY_DIALOG = "Privacy Settings"
# Buttons that close Autodesk's consent page, in order of preference. The page's
# exact labels aren't known yet; privacy_dialog.txt from the first run shows them.
_PRIVACY_CONFIRM_BUTTONS = ("OK", "Continue", "Save", "Done", "Close")

# Inherited AWS settings that would override the mock's credentials, and Maya
# settings that would change which plug-ins or prefs the run uses. In CI the
# environment holds the real OIDC role's credentials. build_mock_environment
# replaces the key, secret and session token, but botocore reads
# AWS_SECURITY_TOKEN before AWS_SESSION_TOKEN, so drop all of them.
_SCRUBBED_ENV_VARS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_SECURITY_TOKEN",
    "AWS_CREDENTIAL_EXPIRATION",
    "AWS_CONFIG_FILE",
    "AWS_SHARED_CREDENTIALS_FILE",
    "AWS_PROFILE",
    "AWS_ROLE_ARN",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
    "MAYA_MODULE_PATH",
    "MAYA_PLUG_IN_PATH",
)

# Keep first-launch prompts and background services from covering the dialog.
_MAYA_QUIET_ENV = {
    # Autodesk Desktop Analytics, whose first-launch "Privacy Settings" consent
    # dialog blocks Maya before it runs any startup command.
    "MAYA_DISABLE_ADP": "1",
    "MAYA_DISABLE_CIP": "1",  # Customer Involvement Program prompt
    "MAYA_DISABLE_CER": "1",  # crash reporter
    "MAYA_DISABLE_CLIC_IPM": "1",  # in-product messages
    "MAYA_NO_HOME": "1",  # Home screen
    "MAYA_CM_DISABLE_ERROR_POPUPS": "1",  # color management popups
}


def _version_key(path: Path) -> tuple[int, ...]:
    return tuple(int(number) for number in re.findall(r"\d+", str(path))) or (0,)


def find_maya_executable() -> Path:
    """Locate GUI Maya; MAYA_EXECUTABLE overrides discovery."""
    override = os.environ.get("MAYA_EXECUTABLE")
    if override:
        path = Path(override)
        if path.is_file():
            return path
        raise FileNotFoundError(f"MAYA_EXECUTABLE={override} does not exist")
    if sys.platform == "win32":
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        candidates = list(program_files.glob("Autodesk/Maya20*/bin/maya.exe"))
    elif sys.platform == "darwin":
        candidates = list(Path("/Applications/Autodesk").glob("maya20*/Maya.app/Contents/bin/maya"))
    else:
        candidates = list(Path("/usr/autodesk").glob("maya20*/bin/maya"))
    candidates = [path for path in candidates if path.is_file()]
    if not candidates:
        raise FileNotFoundError("No GUI Maya installation found. Set MAYA_EXECUTABLE.")
    return max(candidates, key=_version_key)


def build_maya_environment(
    *,
    deadline_endpoint_url: str,
    config_path: Path,
    work_dir: Path,
    scene_file: Path,
) -> dict[str, str]:
    """Environment for the Maya process, pointed at the mock Deadline Cloud service."""
    if not (PLUGIN_ENV_DIR / "Maya.env").is_file():
        raise FileNotFoundError(
            f"{PLUGIN_ENV_DIR / 'Maya.env'} is missing; run `hatch run install` first"
        )
    base_env = {k: v for k, v in os.environ.items() if k not in _SCRUBBED_ENV_VARS}
    env = build_mock_environment(
        base_env,
        deadline_endpoint_url=deadline_endpoint_url,
        config_path=config_path,
        home_dir=work_dir / "home",
    )
    # Autodesk licensing reads the real user profile. DEADLINE_CONFIG_FILE_PATH and
    # MAYA_APP_DIR keep the run isolated, so undo the mock's profile redirection.
    for profile_var in ("HOME", "USERPROFILE"):
        if profile_var in os.environ:
            env[profile_var] = os.environ[profile_var]
        else:
            env.pop(profile_var, None)

    env.update(_MAYA_QUIET_ENV)
    env["AWS_DISABLE_HOST_PREFIX_INJECTION"] = "true"
    env["MAYA_ENV_DIR"] = str(PLUGIN_ENV_DIR)
    env["MAYA_APP_DIR"] = str(work_dir / "maya_app_dir")  # fresh prefs for every test
    env[ENV_STATUS_FILE] = str(work_dir / "opener_status.txt")
    env[ENV_SCENE_FILE] = str(scene_file)
    # Expose Qt widgets to the platform accessibility API (needed on Linux).
    env["QT_ACCESSIBILITY"] = "1"
    env["QT_LINUX_ACCESSIBILITY_ALWAYS_ON"] = "1"
    return env


@dataclass
class MayaSession:
    """A running GUI Maya with the submitter dialog open."""

    process: subprocess.Popen
    work_dir: Path
    opener_status: str

    @property
    def log_file(self) -> Path:
        return self.work_dir / "maya.log"

    def tail_log(self, max_chars: int = 4000) -> str:
        if not self.log_file.exists():
            return "(no Maya log)"
        text = self.log_file.read_text(encoding="utf8", errors="replace")
        return f"--- Maya log (tail) ---\n{text[-max_chars:]}"

    def close(self) -> None:
        """Stop Maya and anything it started."""
        _stop_process_tree(self.process)


def _stop_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        if sys.platform != "win32":
            os.killpg(process.pid, signal.SIGKILL)
        process.kill()
        process.wait(timeout=30)


def launch_maya_with_submitter(
    maya_exe: Path, env: Mapping[str, str], work_dir: Path
) -> MayaSession:
    """Start GUI Maya and wait until the opener reports the submitter is open.

    Raises with the opener's report and Maya's log tail on any failure.
    """
    opener = OPENER.as_posix()  # forward slashes need no escaping inside MEL
    command = f"python(\"exec(compile(open(r'{opener}').read(), r'{opener}', 'exec'))\")"
    log_file = work_dir / "maya.log"
    process = subprocess.Popen(
        [str(maya_exe), "-noAutoloadPlugins", "-log", str(log_file), "-command", command],
        env=dict(env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=(sys.platform != "win32"),
    )
    session = MayaSession(process=process, work_dir=work_dir, opener_status="")
    try:
        status_file = Path(env[ENV_STATUS_FILE])
        deadline = time.monotonic() + OPENER_TIMEOUT
        while time.monotonic() < deadline and not status_file.exists():
            if process.poll() is not None:
                raise RuntimeError(
                    f"Maya exited early (rc={process.returncode})\n{session.tail_log()}"
                )
            _dismiss_privacy_dialog(process.pid, work_dir)
            time.sleep(2.0)
        if not status_file.exists():
            tree_file = _dump_accessibility_tree(process.pid, work_dir)
            raise TimeoutError(
                f"The submitter did not open within {OPENER_TIMEOUT:.0f}s "
                f"(a license or first-launch prompt can block it). "
                f"Maya's accessibility tree: {tree_file}\n{session.tail_log()}"
            )
        session.opener_status = status_file.read_text(encoding="utf8")
        if not session.opener_status.startswith("OK"):
            raise RuntimeError(f"Opener failed inside Maya:\n{session.opener_status}")
        return session
    except BaseException:
        session.close()
        raise


def _maya_apps(pid: int) -> list:
    import xa11y

    return [app for app in xa11y.App.list() if app.pid == pid]


def _dismiss_privacy_dialog(pid: int, work_dir: Path) -> None:
    """Answer Autodesk's first-launch "Privacy Settings" dialog if it is showing.

    On a new user profile, Maya shows this consent page (a WebView window inside
    a native dialog) before it runs any startup command, and none of the MAYA_*
    settings above suppress it. Its tree is saved first, so a run where no button
    matches still shows what the dialog offers. Best effort: any accessibility
    error leaves the dialog for the timeout report.
    """
    try:
        for app in _maya_apps(pid):
            dialog = app.locator(
                ", ".join(
                    f"{role}[name='{PRIVACY_DIALOG}']"
                    for role in ("window", "dialog", "pane", "document", "group")
                )
            )
            if not dialog.exists():
                continue
            tree_file = work_dir / "privacy_dialog.txt"
            if not tree_file.exists():
                tree_file.write_text(dialog.dump(max_depth=8), encoding="utf8")
            for name in _PRIVACY_CONFIRM_BUTTONS:
                button = dialog.descendant(f"button[name='{name}']")
                if button.exists():
                    button.press()
                    return
    except Exception:  # noqa: BLE001
        return


def _dump_accessibility_tree(pid: int, work_dir: Path) -> Optional[Path]:
    """Save Maya's accessibility tree, to show what is blocking it; best effort."""
    try:
        dumps = [app.dump(max_depth=6) for app in _maya_apps(pid)]
    except Exception as error:  # noqa: BLE001
        dumps = [f"Could not read the accessibility tree: {error!r}"]
    path = work_dir / "maya_accessibility_tree.txt"
    path.write_text("\n\n".join(dumps) or "No accessibility app for Maya's process", "utf8")
    return path


def screenshot(path: Path) -> Optional[Path]:
    """Save a screenshot of the desktop for diagnosing a failure; best effort."""
    try:
        import xa11y

        xa11y.screenshot().save_png(str(path))
        return path
    except Exception:
        return None

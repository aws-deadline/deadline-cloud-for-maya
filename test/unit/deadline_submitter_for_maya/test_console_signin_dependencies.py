# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Guards the dependency declarations that AWS Console sign-in depends on.

Console sign-in is not exercised by the integration tests: it needs an interactive
browser OAuth handshake and Deadline Cloud Monitor, while CI authenticates by
assuming a role, so credentials are host-provided and the console path is never
taken. What can break silently is the dependency declaration, which is what these
tests pin.

The tests read ``pyproject.toml`` rather than installed distribution metadata.
``importlib.metadata`` reflects what was captured at install time, so an edit to
``pyproject.toml`` would not be seen until the environment is reinstalled -- and
"somebody edited that line" is precisely the regression being guarded.

Scope matters as much as the versions. The ``console`` extra belongs at bundle time
in ``scripts/deps_bundle.py`` and not on the base dependencies: the base list is
resolved into the adaptor package by ``scripts/create_adaptor_packaging_artifact.sh``
under ``--only-binary=:all: --platform <tag>``, and no awscrt wheel meeting the
floor exists for the ``macosx_10_9_x86_64`` tag that script uses, so pip would
silently walk back to a release with no usable crypto support.
"""

import sys
from pathlib import Path

from packaging.requirements import Requirement

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on Python 3.9 and 3.10 only
    import tomli as tomllib

PYPROJECT = Path(__file__).parents[3] / "pyproject.toml"

# Console sign-in landed in deadline 0.60.4 and nowhere earlier: 0.60.1 through
# 0.60.3 have no AWS_CONSOLE_LOGIN credentials source and do not declare a
# `console` extra at all. 0.60.3 is the highest version that must be excluded.
HIGHEST_DEADLINE_WITHOUT_CONSOLE_SIGNIN = "0.60.3"


def _base_dependencies() -> list[Requirement]:
    project_dict = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert "project" in project_dict, "pyproject.toml has no project table"
    assert "dependencies" in project_dict["project"], "pyproject.toml has no dependencies"
    return [Requirement(r) for r in project_dict["project"]["dependencies"]]


def _deadline_requirements() -> list[Requirement]:
    deadline_reqs = [r for r in _base_dependencies() if r.name == "deadline"]
    assert deadline_reqs, "pyproject.toml declares no requirement on deadline"
    return deadline_reqs


def test_deadline_floor_excludes_releases_without_console_signin():
    """Guards the floor itself, not whatever a resolver happened to select.

    An installed-version check cannot do this: with a loosened ">= 0.60.1"
    requirement, pip still resolves the newest 0.60.x, so the regression passes
    unnoticed. The floor matters even though the console extra is added at bundle
    time: below 0.60.4 no `console` extra exists at all, so pip backtracks past
    the extra to an older deadline, drops awscrt, warns once, and exits 0.
    """
    for req in _deadline_requirements():
        assert not req.specifier.contains(HIGHEST_DEADLINE_WITHOUT_CONSOLE_SIGNIN), (
            f"allows deadline {HIGHEST_DEADLINE_WITHOUT_CONSOLE_SIGNIN}, which has no "
            f"console sign-in support: {req}"
        )


def test_base_dependencies_do_not_request_the_console_extra():
    """Keeps awscrt out of the adaptor package.

    The base list is resolved into the adaptor artifact per platform tag under
    --only-binary=:all:. For macosx_10_9_x86_64 no awscrt wheel meets the floor, so pip
    resolves backwards to one whose crypto support botocore will not accept -- the build
    succeeds and console sign-in is quietly broken. The adaptor never signs in
    interactively, so it has no use for the extra; scripts/deps_bundle.py adds it to the
    submitter's dependency bundle instead.
    """
    for req in _deadline_requirements():
        assert (
            "console" not in req.extras
        ), f"console extra leaks into the adaptor's dependency closure via: {req}"

    # Copying the requirement in directly is the likelier mistake, and has the same effect.
    assert not [
        r for r in _base_dependencies() if r.name == "awscrt"
    ], "awscrt must not be a base dependency; it would be resolved into the adaptor package"

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

import pytest
from packaging.requirements import Requirement

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on Python 3.9 and 3.10 only
    import tomli as tomllib

SCRIPTS_DIR = Path(__file__).parents[3] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    # Appended rather than prepended: scripts/ holds generically named modules, and
    # prepending would shadow any same-named import for the rest of the pytest session.
    sys.path.append(str(SCRIPTS_DIR))

import deps_bundle  # noqa: E402
import install_dev_submitter  # noqa: E402
from _project import Dependency  # noqa: E402

PYPROJECT = Path(__file__).parents[3] / "pyproject.toml"

# Console sign-in landed in deadline 0.60.4 and nowhere earlier: these releases have
# no AWS_CONSOLE_LOGIN credentials source and do not declare a `console` extra at
# all, so every one of them must be excluded by the floor.
DEADLINE_VERSIONS_WITHOUT_CONSOLE_SIGNIN = ["0.60.1", "0.60.2", "0.60.3"]


def _base_dependencies() -> list[Requirement]:
    project_dict = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert "project" in project_dict, "pyproject.toml has no project table"
    assert "dependencies" in project_dict["project"], "pyproject.toml has no dependencies"
    return [Requirement(r) for r in project_dict["project"]["dependencies"]]


def _deadline_requirements() -> list[Requirement]:
    deadline_reqs = [r for r in _base_dependencies() if r.name == "deadline"]
    assert deadline_reqs, "pyproject.toml declares no requirement on deadline"
    return deadline_reqs


@pytest.mark.parametrize("bad_version", DEADLINE_VERSIONS_WITHOUT_CONSOLE_SIGNIN)
def test_deadline_floor_excludes_releases_without_console_signin(bad_version):
    """Guards the floor itself, not whatever a resolver happened to select.

    An installed-version check cannot do this: with a loosened ">= 0.60.1"
    requirement, pip still resolves the newest 0.60.x, so the regression passes
    unnoticed. The floor matters even though the console extra is added at bundle
    time: below 0.60.4 no `console` extra exists at all, so pip backtracks past
    the extra to an older deadline, drops awscrt, warns once, and exits 0.

    Every known-bad version is checked individually rather than only the highest:
    a "pin around a bad release" edit like `>= 0.60.1, != 0.60.3` excludes the
    sample while still admitting 0.60.1 and 0.60.2.
    """
    for req in _deadline_requirements():
        assert not req.specifier.contains(
            bad_version
        ), f"allows deadline {bad_version}, which has no console sign-in support: {req}"


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


def test_deps_bundle_requests_the_console_extra():
    """The submitter resolves through the deps bundle, so console is added there.

    Applies the bundler's own rewrite to the requirement pyproject.toml actually
    declares, so a rename or a pre-existing extras list cannot silently bypass it.
    """
    for req in _deadline_requirements():
        rewritten = Requirement(deps_bundle._add_console_extra(str(req)))
        assert "console" in rewritten.extras, f"bundler does not add the console extra to: {req}"
        assert rewritten.specifier == req.specifier, "rewrite must preserve the specifier"


@pytest.mark.parametrize(
    "requirement, expected",
    [
        # Plain requirement gains the extra and keeps its specifier.
        ("deadline==0.60.*", "deadline[console]==0.60.*"),
        ("deadline>=0.60.4,<0.61", "deadline[console]>=0.60.4,<0.61"),
        # An existing extra is preserved, not replaced.
        ("deadline[gui]==0.60.*", "deadline[gui,console]==0.60.*"),
        # The extra is not duplicated when already present.
        ("deadline[console]==0.60.*", "deadline[console]==0.60.*"),
        # Non-deadline requirements pass through untouched.
        ("pyside6-essentials==6.8.3", "pyside6-essentials==6.8.3"),
        ("deadline-cloud-for-maya==0.15.*", "deadline-cloud-for-maya==0.15.*"),
    ],
)
def test_add_console_extra_rewrites(requirement, expected):
    """Pins the rewrite _build_base_environment applies to every dependency."""
    assert deps_bundle._add_console_extra(requirement) == expected


def test_dev_submitter_requests_the_console_extra():
    """The dev submitter tree must match the shipped bundle, not the adaptor.

    scripts/install_dev_submitter.py resolves project.dependencies through pipgrip
    rather than deps_bundle, so it needs its own application of the rewrite --
    otherwise a dev install silently lacks console sign-in while the installer-built
    submitter has it. Exercised through _project.Dependency because its .spec keeps
    pyproject.toml's spacing, which the rewrite must strip to match the name.
    """
    specs = install_dev_submitter._specs_for_pipgrip(
        [Dependency(str(req)) for req in _deadline_requirements()]
        + [Dependency("deadline >= 0.60.4,< 0.61"), Dependency("xxhash == 3.*")]
    )
    for spec in specs:
        rewritten = Requirement(spec)
        if rewritten.name == "deadline":
            assert "console" in rewritten.extras, f"dev install misses the console extra: {spec}"
        else:
            assert not rewritten.extras, f"unexpected extras on {spec}"


def test_dev_submitter_leaves_other_specs_byte_for_byte():
    """Non-deadline specs must not be whitespace-normalized.

    The dev installer's list includes --local-dep checkouts' requirement strings.
    Removing every space corrupts multi-clause environment markers ('... >= "3.10"
    and ...' is not tokenizable as '..."3.10"and...'), so the stripped form may only
    be used for the deadline requirement the rewrite fires on.
    """
    marker_spec = 'foo >= 1.0; python_version >= "3.10" and sys_platform == "win32"'
    specs = install_dev_submitter._specs_for_pipgrip(
        [Dependency(marker_spec), Dependency("deadline == 0.60.*")]
    )
    assert specs == [marker_spec, "deadline[console]==0.60.*"]

    # And with the extra disabled (Maya 2023 on macOS), everything passes through.
    specs = install_dev_submitter._specs_for_pipgrip(
        [Dependency(marker_spec), Dependency("deadline == 0.60.*")], add_console_extra=False
    )
    assert specs == [marker_spec, "deadline == 0.60.*"]


def test_dev_submitter_pulls_console_requirements_from_a_local_deadline():
    """--local-dep ../deadline-cloud filters the deadline requirement out entirely.

    The rewrite then has nothing to fire on, so the extra's own contents must be
    read from the local checkout's optional-dependencies instead -- otherwise the
    environment most likely to be debugging console sign-in is the one without it.
    """
    local_deadline = {
        "project": {
            "name": "deadline",
            "optional-dependencies": {"console": ["awscrt>=0.28.4", "botocore[crt]>=1.34.0"]},
        }
    }
    other_local = {"project": {"name": "openjd-model"}}
    requirements = install_dev_submitter._console_extra_requirements([local_deadline, other_local])
    assert [req.spec for req in requirements] == ["awscrt>=0.28.4", "botocore[crt]>=1.34.0"]

    assert install_dev_submitter._console_extra_requirements([other_local]) == []

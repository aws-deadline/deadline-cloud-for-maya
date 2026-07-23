# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Tests for the unified MayaSubmitter (deadline.maya_submitter.submitter).

`maya` and related modules are mocked in this package's __init__.py.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from deadline.client.exceptions import DeadlineOperationError
from deadline.maya_submitter.render_layers import LayerSelection
from deadline.maya_submitter.submitter import (
    MayaSceneContext,
    MayaSubmitter,
    MayaSubmitterSettings,
)

# The module object MayaSubmitter actually lives in. Other test modules
# (scripts/test_submitter.py, scripts/test_submission_api.py) pop
# `deadline.maya_submitter.submitter` from sys.modules and re-import it, which
# under pytest-xdist can leave a *different* module object in sys.modules than
# the one this file imported. Patching module globals (e.g.
# get_current_render_layer_name) by dotted-path string would then target the
# wrong object and miss. Patching via this reference — the same module whose
# _prepare_render_layers_for_submission does the lookup — is reload-safe.
_submitter_module = sys.modules[MayaSubmitter.__module__]


def _layer(name: str, renderer: str, frame_range: str = "1-10") -> MagicMock:
    """A stand-in RenderLayerData with the attributes the prep/builders read."""
    layer = MagicMock()
    layer.name = name
    layer.display_name = name
    layer.renderer_name = renderer
    layer.frame_range = frame_range
    layer.output_file_prefix = "<Scene>"
    layer.image_resolution = (1920, 1080)
    # Prep assigns these per-layer parameter names when ranges/resolutions differ;
    # start them as None so a single-layer or uniform context leaves them unset.
    layer.frames_parameter_name = None
    layer.output_file_prefix_parameter_name = None
    layer.image_width_parameter_name = None
    layer.image_height_parameter_name = None
    return layer


def _context(layers: list) -> MayaSceneContext:
    return MayaSceneContext(
        render_layers=layers,
        current_layer_selectable_cameras=[],
        all_layer_selectable_cameras=[],
    )


# ---------------------------------------------------------------------------
# _prepare_render_layers_for_submission — the CURRENT-layer guard
#
# CURRENT-layer narrowing moved out of the old MayaSubmitterAPI._filter_layers_for_selection
# and into the shared _prepare_render_layers_for_submission, so the GUI path and
# the unified API path filter identically.
# ---------------------------------------------------------------------------


def test_prepare_all_returns_every_renderer():
    layers = [_layer("layer1", "arnold"), _layer("layer2", "vray")]
    settings = MayaSubmitterSettings()  # render_layer_selection defaults to ALL
    settings.override_frame_range = True

    prepared = MayaSubmitter._prepare_render_layers_for_submission(settings, _context(layers))

    assert {layer.name for layer in prepared.layers} == {"layer1", "layer2"}
    assert prepared.renderers == {"arnold", "vray"}


@patch.object(_submitter_module, "get_current_render_layer_name", return_value="layer2")
def test_prepare_current_narrows_to_current(mock_current):
    layers = [_layer("layer1", "arnold"), _layer("layer2", "vray")]
    settings = MayaSubmitterSettings()
    settings.render_layer_selection = LayerSelection.CURRENT
    settings.override_frame_range = True

    prepared = MayaSubmitter._prepare_render_layers_for_submission(settings, _context(layers))

    assert [layer.name for layer in prepared.layers] == ["layer2"]
    assert prepared.renderers == {"vray"}


@patch.object(_submitter_module, "get_current_render_layer_name", return_value="not_renderable")
def test_prepare_current_not_renderable_raises(mock_current):
    layers = [_layer("layer1", "arnold")]
    settings = MayaSubmitterSettings()
    settings.render_layer_selection = LayerSelection.CURRENT

    with pytest.raises(DeadlineOperationError, match="not set as renderable"):
        MayaSubmitter._prepare_render_layers_for_submission(settings, _context(layers))


def test_prepare_duplicate_display_names_raise():
    # Two distinct layers sharing a display name would collide on the per-layer
    # parameter names (e.g. "<display>Frames"), silently dropping one layer's
    # values. The prep must reject this loudly instead.
    layer_a = _layer("layerA", "arnold", frame_range="1-10")
    layer_b = _layer("layerB", "vray", frame_range="1-20")
    layer_b.display_name = "layerA"  # collide on display name, distinct .name
    settings = MayaSubmitterSettings()  # ALL selection
    settings.override_frame_range = False

    with pytest.raises(DeadlineOperationError, match="unique display names"):
        MayaSubmitter._prepare_render_layers_for_submission(settings, _context([layer_a, layer_b]))


# ---------------------------------------------------------------------------
# MayaSubmitter.get_parameter_values — renderers must be derived AFTER the
# CURRENT filter (regression guard for the multi-layer renderer-scoping bug).
# ---------------------------------------------------------------------------


@patch.object(MayaSubmitter, "_get_parameter_values")
@patch.object(_submitter_module, "get_current_render_layer_name", return_value="cur")
def test_get_parameter_values_renderers_scoped_to_current_layer(mock_current, mock_get_values):
    # scene has an Arnold layer (not submitted) and a vray CURRENT layer.
    layers = [_layer("other", "arnold"), _layer("cur", "vray")]
    mock_get_values.return_value = []

    # Inject the scene context so no real Maya scan happens.
    api = MayaSubmitter(scene_context=_context(layers))
    settings = MayaSubmitterSettings()
    settings.render_layer_selection = LayerSelection.CURRENT
    settings.override_frame_range = True

    api.get_parameter_values(settings, [])

    # renderers arg (2nd positional) must contain only the submitted layer's
    # renderer — not arnold from the non-submitted layer.
    _settings, renderers, render_layers, _qp = mock_get_values.call_args.args
    assert renderers == {"vray"}
    assert [layer.name for layer in render_layers] == ["cur"]


# ---------------------------------------------------------------------------
# Stateful scene-context caching — the query-once optimization.
# ---------------------------------------------------------------------------


def test_scene_context_built_lazily_once():
    ctx = _context([_layer("layer1", "arnold")])
    with patch.object(_submitter_module, "create_scene_context", return_value=ctx) as mock_create:
        api = MayaSubmitter()
        mock_create.assert_not_called()  # nothing scanned until first access

        first = api.scene_context
        second = api.scene_context

    assert first is ctx
    assert second is ctx
    mock_create.assert_called_once()  # cached — scene scanned exactly once


def test_injected_scene_context_is_not_rescanned():
    ctx = _context([_layer("layer1", "arnold")])
    with patch.object(_submitter_module, "create_scene_context") as mock_create:
        api = MayaSubmitter(scene_context=ctx)
        assert api.scene_context is ctx
    mock_create.assert_not_called()


def test_reset_scene_context_forces_rescan():
    first_ctx = _context([_layer("layer1", "arnold")])
    second_ctx = _context([_layer("layer2", "vray")])
    with patch.object(
        _submitter_module, "create_scene_context", side_effect=[first_ctx, second_ctx]
    ) as mock_create:
        api = MayaSubmitter()
        assert api.scene_context is first_ctx
        api.reset_scene_context()
        assert api.scene_context is second_ctx

    assert mock_create.call_count == 2


def test_job_template_and_parameter_values_share_one_scan():
    """Both builder methods must reuse the single cached context."""
    ctx = _context([_layer("layer1", "arnold")])
    settings = MayaSubmitterSettings()
    settings.override_frame_range = True

    with (
        patch.object(_submitter_module, "create_scene_context", return_value=ctx) as mock_create,
        patch.object(MayaSubmitter, "_get_job_template", return_value={"steps": []}),
        patch.object(MayaSubmitter, "_get_parameter_values", return_value=[]),
        patch.object(_submitter_module, "get_default_job_template", return_value={}),
    ):
        api = MayaSubmitter()
        api.get_job_template(settings)
        api.get_parameter_values(settings, [])

    mock_create.assert_called_once()

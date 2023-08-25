# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest
from deadline.client.job_bundle.adaptors import (
    DCC_BACKGROUND_END_SCRIPT,
    DCC_BACKGROUND_START_SCRIPT,
    RUN_SCRIPT,
)

import deadline_submitter_for_maya.scripts.aws_deadline.commands.maya_render_submitter as module_maya_render_submitter
from deadline_submitter_for_maya.scripts.aws_deadline.commands.maya_render_submitter import (
    LayerCameraCombo,
    _get_job_template,
    _get_parameter_values,
    _get_render_layers,
)
from deadline_submitter_for_maya.scripts.aws_deadline.data_classes.render_submitter_settings import (
    RenderSubmitterUISettings,
)
from deadline_submitter_for_maya.scripts.aws_deadline.render_layers import LayerSelection

OGRE_LAYER = MagicMock(display_name="Ogre")
EMPTY_LAYER = MagicMock(display_name="")

ONION_CAMERA = MagicMock()
ONION_CAMERA.name = "Onion"

JOB_TEMPLATE = {
    "specificationVersion": "2022-09-01",
    "name": "scene",
    "steps": [
        {
            "name": "Layer:Ogre-Camera:Onion",
            "parameterSpace": {"parameters": [{"name": "frame", "range": [1], "type": "INT"}]},
            "environments": [
                {
                    "name": "Rez",
                    "description": "Initializes and destroys the Rez environment for the run",
                    "script": {
                        "actions": {
                            "onEnter": {
                                "command": "/usr/local/bin/deadline-rez",
                                "args": [
                                    "init",
                                    "-d",
                                    "{{ Session.WorkingDirectory }}",
                                    "mayaIO",
                                    "mtoa",
                                    "deadline_maya",
                                ],
                            },
                            "onExit": {
                                "command": "/usr/local/bin/deadline-rez",
                                "args": ["destroy", "-d", "{{ Session.WorkingDirectory }}"],
                            },
                        }
                    },
                },
                {
                    "name": "Maya",
                    "description": "Environment that starts the Maya Adaptor in background mode.",
                    "script": {
                        "embeddedFiles": [
                            {"type": "TEXT", "data": "data that we had to mock out..."},
                            {
                                "name": "start",
                                "type": "TEXT",
                                "runnable": True,
                                "data": DCC_BACKGROUND_START_SCRIPT.format(dcc_name="Maya"),
                            },
                            {
                                "name": "end",
                                "type": "TEXT",
                                "runnable": True,
                                "data": DCC_BACKGROUND_END_SCRIPT.format(dcc_name="Maya"),
                            },
                        ],
                        "actions": {
                            "onEnter": {
                                "command": "{{ Env.File.start }}",
                                "cancelation": {
                                    "mode": "NOTIFY_THEN_TERMINATE",
                                    "notifyPeriodInSeconds": 90,
                                },
                            },
                            "onExit": {
                                "command": "{{ Env.File.end }}",
                                "cancelation": {
                                    "mode": "NOTIFY_THEN_TERMINATE",
                                    "notifyPeriodInSeconds": 90,
                                },
                            },
                        },
                    },
                },
            ],
            "script": {
                "embeddedFiles": [
                    {"name": "runData", "type": "TEXT", "data": "frame: {{ Task.Param.frame }}"},
                    {
                        "name": "run",
                        "type": "TEXT",
                        "runnable": True,
                        "data": RUN_SCRIPT.format(dcc_name="Maya"),
                    },
                ],
                "actions": {
                    "onRun": {
                        "command": "{{ Task.File.run }}",
                        "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                    }
                },
            },
        }
    ],
}


INIT_DATA_ATTACHMENT = {
    "type": "TEXT",
    "data": "data that we had to mock out...",
}

PARAMETER_VALUES = {
    "parameterValues": [
        {"name": "deadline:priority", "value": 51},
        {"name": "deadline:targetTaskRunStatus", "value": "READY"},
        {"name": "deadline:maxFailedTasksCount", "value": 123},
        {"name": "deadline:maxRetriesPerTask", "value": 321},
    ]
}

MOCK_RENDERER = MagicMock()
MOCK_RENDERER.get_output_directories.return_value = ["/path/to/output"]

MOCK_RENDERABLE_LAYER = MagicMock()
MOCK_RENDERABLE_LAYER.renderable = True

MOCK_UNRENDERABLE_LAYER = MagicMock()
MOCK_UNRENDERABLE_LAYER.renderable = False


class TestMayaRenderSubmitter:
    @pytest.mark.parametrize(
        "combo,result",
        [
            (LayerCameraCombo(layer=OGRE_LAYER, camera=ONION_CAMERA), "Layer:Ogre-Camera:Onion"),
            (LayerCameraCombo(layer=OGRE_LAYER), "Layer:Ogre"),
            (LayerCameraCombo(layer=EMPTY_LAYER), "Layer:"),
        ],
    )
    def test_layer_camer_combo_name(self, combo: LayerCameraCombo, result: str):
        assert combo.name == result

    @patch.object(
        module_maya_render_submitter, "_get_init_data_attachment", return_value=INIT_DATA_ATTACHMENT
    )
    def test_get_job_template(self, _mock_init_attachment: Mock) -> None:
        settings = RenderSubmitterUISettings(
            name="scene",
            override_frame_range=True,
            frame_list="1",
            project_path="/path/to/project",
            output_path="/path/to/output",
        )
        layer_camera_combos = [LayerCameraCombo(layer=OGRE_LAYER, camera=ONION_CAMERA)]
        assert _get_job_template(settings, layer_camera_combos) == JOB_TEMPLATE

    def test_get_parameter_values(self) -> None:
        settings = RenderSubmitterUISettings(
            priority=51, initial_state="READY", failed_tasks_limit=123, task_retry_limit=321
        )
        assert _get_parameter_values(settings) == PARAMETER_VALUES

    @patch.object(
        module_maya_render_submitter.RenderLayer,
        "get_all_layers",
        return_value=[MOCK_RENDERABLE_LAYER],
    )
    def test_get_render_layers_all(self, mock_get_all_layers: Mock) -> None:
        settings = RenderSubmitterUISettings(render_layer_selection=LayerSelection.ALL)
        result = _get_render_layers(settings)

        mock_get_all_layers.assert_called_once()
        assert result == [MOCK_RENDERABLE_LAYER]

    @patch.object(
        module_maya_render_submitter.RenderLayer,
        "get_current_layer",
        return_value=MOCK_RENDERABLE_LAYER,
    )
    def test_get_render_layers_current(self, mock_get_current_layer: Mock) -> None:
        settings = RenderSubmitterUISettings(render_layer_selection=LayerSelection.CURRENT)
        result = _get_render_layers(settings)

        mock_get_current_layer.assert_called_once()
        assert result == [MOCK_RENDERABLE_LAYER]

    @patch.object(
        module_maya_render_submitter.RenderLayer,
        "get_current_layer",
        return_value=MOCK_UNRENDERABLE_LAYER,
    )
    @patch.object(module_maya_render_submitter.logger, "error")
    def test_get_render_layers_no_renderable(
        self, mock_logger_error: Mock, mock_get_current_layer: Mock
    ) -> None:
        settings = RenderSubmitterUISettings(render_layer_selection=LayerSelection.CURRENT)

        result = _get_render_layers(settings)
        mock_logger_error.assert_called_once_with(
            "Failed to submit render jobs.  No Renderable Layers found"
        )
        assert result == []

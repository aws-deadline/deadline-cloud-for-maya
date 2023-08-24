# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import Optional
from unittest.mock import Mock, PropertyMock, patch

import pymel.core as pmc  # pylint: disable=import-error
import pytest

import deadline_submitter_for_maya.scripts.aws_deadline.scene as scene_module
from deadline_submitter_for_maya.scripts.aws_deadline.scene import Animation, FrameRange, Scene


class TestFrameRange:
    frame_range_params = [(1, 100, 7), (1, 100, None), (1, None, 7), (10, 10, 10), (1, 10, 1)]

    @pytest.mark.parametrize("start, stop, step", frame_range_params)
    def test_frame_range_iter(self, start: int, stop: int, step: Optional[int]) -> None:
        # GIVEN
        frame_range = FrameRange(start, stop, step)

        # WHEN
        frames = [f for f in frame_range]

        # THEN
        if stop is None:
            stop = start
        if step is None:
            step = 1
        assert frames == [i for i in range(start, stop + step, step)]

    @pytest.mark.parametrize("start, stop, step", frame_range_params)
    def test_frame_repr(self, start: int, stop: int, step: Optional[int]) -> None:
        # GIVEN
        frame_range = FrameRange(start, stop, step)

        # WHEN
        fr_repr = repr(frame_range)

        # THEN
        if stop is None or start == stop:
            assert fr_repr == str(start)
        elif step is None or step == 1:
            assert fr_repr == f"{start}-{stop}"
        else:
            assert fr_repr == f"{start}-{stop}:{step}"


class TestAnimation:
    @pytest.mark.parametrize("activated", [True, False])
    @patch.object(scene_module, "SCENE_REF")
    def test_activated(self, mock_scene: Mock, activated: bool) -> None:
        # GIVEN
        mock_scene.defaultRenderGlobals.animation.get.return_value = activated

        # WHEN
        animation_activated = Animation.activated()

        # THEN
        assert animation_activated == activated
        mock_scene.defaultRenderGlobals.animation.get.assert_called_once()

    @patch.object(scene_module, "pmc")
    def test_current_frame(self, mock_pmc: Mock) -> None:
        # GIVEN
        frames = [i for i in range(10)]
        mock_pmc.getCurrentTime.side_effect = frames

        # WHEN
        animation_frames = [Animation.current_frame() for _ in range(10)]

        # THEN
        assert animation_frames == frames
        assert mock_pmc.getCurrentTime.call_count == 10

    @pytest.mark.parametrize("frame", [1])
    @patch.object(scene_module, "SCENE_REF")
    def test_start_frame(self, mock_scene: Mock, frame: int) -> None:
        # GIVEN
        mock_scene.defaultRenderGlobals.startFrame.get.return_value = frame

        # WHEN
        start_frame = Animation.start_frame()

        # THEN
        assert start_frame == frame
        mock_scene.defaultRenderGlobals.startFrame.get.assert_called_once()

    @pytest.mark.parametrize("frame", [5])
    @patch.object(scene_module, "SCENE_REF")
    def test_end_frame(self, mock_scene: Mock, frame: int) -> None:
        # GIVEN
        mock_scene.defaultRenderGlobals.endFrame.get.return_value = frame

        # WHEN
        end_frame = Animation.end_frame()

        # THEN
        assert end_frame == frame
        mock_scene.defaultRenderGlobals.endFrame.get.assert_called_once()

    @pytest.mark.parametrize("frame_step", [5])
    @patch.object(scene_module, "SCENE_REF")
    def test_frame_step(self, mock_scene, frame_step: int) -> None:
        # GIVEN
        mock_scene.defaultRenderGlobals.byFrameStep.get.return_value = frame_step

        # WHEN
        animation_frame_step = Animation.frame_step()

        # THEN
        assert animation_frame_step == frame_step
        mock_scene.defaultRenderGlobals.byFrameStep.get.assert_called_once()

    def test_extension_padding(self) -> None:
        # GIVEN
        return_value = pmc.SCENE.defaultRenderGlobals.extensionPadding.get.return_value

        # WHEN
        animation_extension_padding = Animation.extension_padding()

        # THEN
        assert animation_extension_padding == return_value
        pmc.SCENE.defaultRenderGlobals.extensionPadding.get.assert_called_once()

    @pytest.mark.parametrize("start, stop, step", [(1, 100, 5)])
    @patch.object(scene_module, "SCENE_REF")
    def test_frame_list(self, mock_scene: Mock, start: int, stop: int, step: int) -> None:
        # GIVEN
        mock_scene.defaultRenderGlobals.startFrame.get.return_value = start
        mock_scene.defaultRenderGlobals.endFrame.get.return_value = stop
        mock_scene.defaultRenderGlobals.byFrameStep.get.return_value = step

        # WHEN
        frame_list = Animation.frame_list()

        # THEN
        assert frame_list.start == start
        assert frame_list.stop == stop
        assert frame_list.step == step
        mock_scene.defaultRenderGlobals.startFrame.get.assert_called_once()
        mock_scene.defaultRenderGlobals.endFrame.get.assert_called_once()
        mock_scene.defaultRenderGlobals.byFrameStep.get.assert_called_once()


class TestScene:
    @pytest.mark.parametrize("name", ["fast_and_furious_28"])
    @patch.object(scene_module, "pmc")
    def test_name(self, mock_pmc: Mock, name: str) -> None:
        # GIVEN
        mock_pmc.sceneName.return_value = name

        # WHEN
        scene_name = Scene.name()

        # THEN
        assert scene_name == name
        mock_pmc.sceneName.assert_called_once()

    @pytest.mark.parametrize("renderer", ["mayaSoftware"])
    @patch.object(scene_module, "SCENE_REF")
    def test_renderer(self, mock_scene: Mock, renderer: str) -> None:
        # GIVEN
        mock_scene.defaultRenderGlobals.currentRenderer.get.return_value = renderer

        # WHEN
        scene_renderer = Scene.renderer()

        # THEN
        assert scene_renderer == renderer
        mock_scene.defaultRenderGlobals.currentRenderer.get.assert_called_once()

    @pytest.mark.parametrize("project_path", ["/tmp/path/to/a/project"])
    @patch.object(scene_module, "pmc")
    def test_project_path(self, mock_pmc: Mock, project_path: str) -> None:
        # GIVEN
        mock_pmc.workspace.path = project_path

        # WHEN
        scene_project_path = Scene.project_path()

        # THEN
        assert scene_project_path == project_path

    @pytest.mark.parametrize("output_path", ["/tmp/put/output/here", ""])
    @patch.object(scene_module, "pmc")
    def test_output_path(self, mock_pmc: Mock, output_path: str) -> None:
        # GIVEN
        mock_pmc.workspace.fileRules.get.return_value = output_path
        mock_pmc.workspace.path.return_value = PropertyMock(return_value="some/project/path")

        # WHEN
        scene_output_path = Scene.output_path()

        # THEN
        if output_path:
            assert scene_output_path == output_path
        else:
            assert scene_output_path == str(mock_pmc.workspace.path)
        mock_pmc.workspace.fileRules.get.assert_called_once_with("images")

    @pytest.mark.parametrize("autotx_enabled", [True, False])
    @pytest.mark.parametrize("arnold_loaded", [True, False])
    @patch.object(scene_module, "SCENE_REF")
    def test_autotx(self, mock_scene: Mock, autotx_enabled: bool, arnold_loaded: bool) -> None:
        # GIVEN
        mock_scene.defaultArnoldRenderOptions.autotx.get.return_value = autotx_enabled
        mock_scene.defaultRenderGlobals.currentRenderer.get.return_value = (
            "arnold" if arnold_loaded else "mayaSoftware"
        )
        # WHEN
        scene_autotx = Scene.autotx()

        # THEN
        assert scene_autotx == (autotx_enabled and arnold_loaded)
        if arnold_loaded:
            mock_scene.defaultArnoldRenderOptions.autotx.get.assert_called_once()
        else:
            mock_scene.defaultArnoldRenderOptions.autotx.get.assert_not_called()

    @pytest.mark.parametrize("use_tx", [True, False])
    @pytest.mark.parametrize("arnold_loaded", [True, False])
    @patch.object(scene_module, "SCENE_REF")
    def test_use_existing_tiled_textures(
        self, mock_scene: Mock, use_tx: bool, arnold_loaded: bool
    ) -> None:
        # GIVEN
        mock_scene.defaultArnoldRenderOptions.use_existing_tiled_textures.get.return_value = use_tx
        mock_scene.defaultRenderGlobals.currentRenderer.get.return_value = (
            "arnold" if arnold_loaded else "mayaSoftware"
        )

        # WHEN
        scene_use_tx = Scene.use_existing_tiled_textures()

        # THEN
        assert scene_use_tx == (use_tx and arnold_loaded)
        if arnold_loaded:
            mock_scene.defaultArnoldRenderOptions.use_existing_tiled_textures.get.assert_called_once()  # noqa: E501
        else:
            mock_scene.defaultArnoldRenderOptions.use_existing_tiled_textures.get.assert_not_called()  # noqa: E501

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from .maya_handler_base import MayaHandlerBase

try:
    import pymel.core as pm
except ModuleNotFoundError:  # pragma: no cover
    raise OSError("Could not find the pymel module. Are you running this inside of MayaPy?")


class ArnoldHandler(MayaHandlerBase):
    """Render Handler for Arnold"""

    def __init__(self):
        """
        Initializes the Arnold Renderer and Arnold Renderer Handler
        """
        super().__init__()
        self.action_dict["error_on_arnold_license_fail"] = self.set_error_on_arnold_license_fail
        self.render_kwargs["batch"] = True

    def start_render(self, data: dict) -> None:
        """
        Starts a render in the mayasoftware renderer.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame']

        Raises:
            RuntimeError: If no camera was specified and no renderable camera was found
        """
        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: start_render called without a frame number.")
        self.render_kwargs["seq"] = frame

        if "camera" not in self.render_kwargs:
            try:
                camera = next(cam for cam in pm.ls(cameras=1) if cam.renderable.get())
                print(
                    f"No camera was specified, defaulting to render on {camera}.",
                    flush=True,
                )
                self.render_kwargs["camera"] = camera
            except StopIteration:
                raise RuntimeError(
                    "No camera was specified, and no renderable camera could be found."
                )
        if "width" not in self.render_kwargs:
            self.render_kwargs["width"] = pm.SCENE.defaultResolution.width.get()
            print(
                f"No width was specified, defaulting to {self.render_kwargs['width']}",
                flush=True,
            )
        if "height" not in self.render_kwargs:
            self.render_kwargs["height"] = pm.SCENE.defaultResolution.height.get()
            print(
                f"No height was specified, defaulting to {self.render_kwargs['height']}",
                flush=True,
            )

        # Set the arnold render type so that we don't just make .ass files, but the actual image
        pm.SCENE.defaultArnoldRenderOptions.renderType.set(0)
        if int(pm.SCENE.defaultArnoldRenderOptions.log_verbosity.get()) < 2:
            # min level for progress reporting
            pm.SCENE.defaultArnoldRenderOptions.log_verbosity.set(2)
        pm.arnoldRender(**self.render_kwargs)
        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)

    def set_error_on_arnold_license_fail(self, data: dict) -> None:
        """
        Sets the property that makes Maya fail if there is no Arnold License.
        If set to False the render will complete with a watermark.

        Args:
            data (dict): : The data given from the Adaptor. Keys expected:
                ['error_on_arnold_license_fail']
        """
        val = data.get("error_on_arnold_license_fail", True)
        pm.SCENE.defaultArnoldRenderOptions.abortOnLicenseFail.set(val)

    def set_camera(self, data: dict) -> None:
        """
        Sets the Camera that will be renderered.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['camera']

        Raises:
            RuntimeError: If the camera is not renderable or does not exist
        """
        self.render_kwargs["camera"] = self._find_camera(data)

    def set_render_layer(self, data: dict) -> None:
        """
        Sets the render layer.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['render_layer']

        Raises:
            RuntimeError: If the render layer cannot be found
        """
        pm.editRenderLayerGlobals(currentRenderLayer=self._find_render_layer(data))

    def set_image_height(self, data: dict) -> None:
        """
        Sets the image height.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_height']
        """
        yresolution = int(data.get("image_height", 0))
        if yresolution:
            self.render_kwargs["height"] = yresolution

    def set_image_width(self, data: dict) -> None:
        """
        Sets the image width.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_width']
        """
        xresolution = int(data.get("image_width", 0))
        if xresolution:
            self.render_kwargs["width"] = xresolution

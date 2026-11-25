# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Render a fixture directly in Maya, independently of the Deadline adaptor.

Invoked in a separate mayapy process so the reference and adaptor do not share
scene state or hold renderer licenses simultaneously.
"""

import json
import sys


def main():
    import maya.standalone
    import maya.cmds as cmds

    request = json.loads(sys.argv[1])
    renderer = request["renderer"]
    plugins = {"arnold": "mtoa", "vray": "vrayformaya", "redshift": "redshift4maya"}
    maya.standalone.initialize(name="python")
    try:
        cmds.loadPlugin(plugins[renderer], quiet=True)
        cmds.workspace(request["project"], openWorkspace=True)
        cmds.file(request["scene"], open=True, force=True)
        cmds.editRenderLayerGlobals(currentRenderLayer="defaultRenderLayer")
        cmds.workspace(fileRule=["images", request["output"]])
        cmds.setAttr("defaultRenderGlobals.currentRenderer", renderer, type="string")
        cmds.setAttr("defaultRenderGlobals.imageFilePrefix", request["prefix"], type="string")
        cmds.setAttr("defaultResolution.width", request["width"])
        cmds.setAttr("defaultResolution.height", request["height"])
        cmds.currentTime(request["frame"])
        if renderer == "arnold":
            cmds.setAttr("defaultArnoldRenderOptions.abortOnLicenseFail", True)
            cmds.arnoldRender(batch=True, seq=request["frame"], camera=request["camera"])
        elif renderer == "vray":
            cmds.setAttr("vraySettings.fileNamePrefix", request["prefix"], type="string")
            cmds.setAttr("vraySettings.width", request["width"])
            cmds.setAttr("vraySettings.height", request["height"])
            cmds.setAttr("vraySettings.animType", 2)
            cmds.setAttr("vraySettings.animFrames", str(request["frame"]), type="string")
            cmds.setAttr("vraySettings.vrscene_render_on", 1)
            cmds.setAttr("vraySettings.vrscene_on", 0)
            cmds.setAttr("vraySettings.dontSaveImage", 0)
            cmds.setAttr("vraySettings.noAlpha", 0)
            cmds.setAttr("vraySettings.dontSaveRgbChannel", 0)
            cmds.setAttr("vraySettings.sys_distributed_rendering_on", 0)
            cmds.vrend(camera=request["camera"])
        elif renderer == "redshift":
            cmds.setAttr("defaultRenderGlobals.animation", True)
            cmds.setAttr("defaultRenderGlobals.startFrame", request["frame"])
            cmds.setAttr("defaultRenderGlobals.endFrame", request["frame"])
            cmds.rsRender(render=True, batch=True, animation=True, camera=request["camera"])
    finally:
        maya.standalone.uninitialize()


if __name__ == "__main__":
    main()

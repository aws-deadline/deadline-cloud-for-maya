"""TEMPORARY diagnostic for the Maya 2027 render SIGABRT. Runs under mayapy.

Round 1 (ogsRender per format) passed completely on the fleet: VP2, the GL
stack and libpng all work in-process. The scene pins mayaHardware2 (short
attr ".ren"), so the renderer was correct all along; the discriminator is
that the failing cmds.render() runs print the batch loop's
"Rendering using N render processes." (rUnixMPRenderNumProcs) -- Maya's Unix
multi-process fork mode -- which in-process ogsRender, macOS, and no passing
2027 run ever entered.

Hypothesis: forked render children in 2027 inherit an unusable GL state (fork
plus a live GL context is undefined), return garbage, and the parent's
composite hands libpng garbage dimensions. 2025/2026 survive the same loop,
so 2027 plausibly moved its GL init ahead of the fork.

Test: cmds.render() -- the adaptor's exact call -- single-process first
(defaultRenderGlobals.numCpusToUse=1), then the default last, since it is
expected to abort the interpreter.

Delete this file and its hook in run-integ-tests.py when the investigation ends.
"""

import os
import struct
import sys
import traceback

MODES = [("colormanagement-OFF", False), ("colormanagement-ON", True)]


def log(msg):
    print(f"[swdiag] {msg}", flush=True)


def describe_file(path):
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        head = fh.read(33)
    detail = f"{os.path.basename(path)}  size={size}  head={head[:12].hex()}"
    if head[:8] == b"\x89PNG\r\n\x1a\n" and len(head) >= 24:
        width, height = struct.unpack(">II", head[16:24])
        detail += f"  PNG IHDR says {width}x{height}"
    return detail


def main():
    import maya.standalone

    maya.standalone.initialize()
    import maya.cmds as cmds

    log(f"Maya {cmds.about(version=True)}  cut {cmds.about(cutIdentifier=True)}")

    scene = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "test/integ/test_scripts/minimal_test/scene/test.ma",
    )
    cmds.file(scene, open=True, force=True)
    log(f"current renderer: {cmds.getAttr('defaultRenderGlobals.currentRenderer')}")

    cmds.setAttr("defaultResolution.width", 960)
    cmds.setAttr("defaultResolution.height", 540)
    cmds.setAttr("defaultRenderGlobals.imageFormat", 32)  # PNG, as the test uses
    cmds.setAttr("defaultRenderGlobals.startFrame", 1)
    cmds.setAttr("defaultRenderGlobals.endFrame", 1)

    log(f"scene cfp: {cmds.colorManagementPrefs(query=True, configFilePath=True)}")
    log(f"cm enabled initially: {cmds.colorManagementPrefs(query=True, cmEnabled=True)}")
    cmds.setAttr("defaultRenderGlobals.numCpusToUse", 1)

    for label, cm_on in MODES:
        cmds.colorManagementPrefs(edit=True, cmEnabled=cm_on)
        cmds.setAttr("defaultRenderGlobals.imageFilePrefix", f"swdiag_{label}", type="string")
        log(f"--- cmds.render, cmEnabled={cm_on} ({label}) ---")
        try:
            result = cmds.render("sideCam1", x=960, y=540)
            log(f"render returned: {result}")
            if result and os.path.isfile(str(result)):
                log(f"  {describe_file(str(result))}")
                try:
                    import PIL.Image

                    with PIL.Image.open(str(result)) as img:
                        log(f"  PIL: {img.format} {img.size}")
                except Exception as exc:
                    log(f"  PIL: UNREADABLE: {exc}")
            else:
                log(f"  returned path missing on disk: {result!r}")
        except Exception:
            log(f"render raised:\n{traceback.format_exc()}")

    log("diagnostic completed without aborting")
    maya.standalone.uninitialize()


if __name__ == "__main__":
    sys.exit(main())

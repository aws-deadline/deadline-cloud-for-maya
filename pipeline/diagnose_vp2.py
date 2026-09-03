"""TEMPORARY diagnostic for the Maya 2027 VP2/libpng SIGABRT. Runs under mayapy.

Renders the minimal_test scene with mayaHardware2 (ogsRender) directly -- no
adaptor, no openjd -- once per image format, and inspects what lands on disk.

Order matters: IFF (Maya native, no libpng) then TIFF, then PNG last, because
the PNG write is expected to abort the interpreter. Whatever prints before the
abort is the evidence:

- IFF valid + PNG absent/garbage-header -> framebuffer readback is fine and
  only the libpng encode path is broken (a newer libpng staged into Maya's lib
  becomes a credible fix).
- IFF also missing/garbage -> the VP2 offscreen readback itself is broken and
  no libpng change can help.

Delete this file and pipeline/run-vp2-diag.py when the investigation ends.
"""

import glob
import os
import struct
import sys
import traceback

OUT_DIR = "/tmp/vp2diag"

# defaultRenderGlobals.imageFormat codes
FORMATS = [("iff", 7), ("tif", 3), ("png", 32)]


def log(msg):
    print(f"[vp2diag] {msg}", flush=True)


def describe_file(path):
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        head = fh.read(33)
    detail = f"{os.path.basename(path)}  size={size}  head={head[:12].hex()}"
    if head[:8] == b"\x89PNG\r\n\x1a\n" and len(head) >= 24:
        width, height = struct.unpack(">II", head[16:24])
        detail += f"  PNG IHDR says {width}x{height}"
    return detail


def inspect_outputs(tag):
    files = sorted(glob.glob(os.path.join(OUT_DIR, "**", "*.*"), recursive=True))
    log(f"{tag}: {len(files)} file(s) in {OUT_DIR}")
    for path in files:
        try:
            log(f"  {describe_file(path)}")
        except OSError as exc:
            log(f"  {path}: unreadable: {exc}")
    # PIL parse is the strongest validity check and mirrors the test's comparison.
    try:
        import PIL.Image

        for path in files:
            try:
                with PIL.Image.open(path) as img:
                    log(f"  PIL: {os.path.basename(path)} -> {img.format} {img.size}")
            except Exception as exc:
                log(f"  PIL: {os.path.basename(path)} -> UNREADABLE: {exc}")
    except ImportError:
        log("  (PIL unavailable; header inspection only)")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for stale in glob.glob(os.path.join(OUT_DIR, "**", "*.*"), recursive=True):
        os.unlink(stale)

    import maya.standalone

    maya.standalone.initialize()
    import maya.cmds as cmds

    log(f"Maya {cmds.about(version=True)}  cut {cmds.about(cutIdentifier=True)}")
    log(f"MAYA_VP2_DEVICE_OVERRIDE={os.environ.get('MAYA_VP2_DEVICE_OVERRIDE')}")

    scene = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "test/integ/test_scripts/minimal_test/scene/test.ma",
    )
    cmds.file(scene, open=True, force=True)
    log(f"opened {scene}")

    # What VP2 reports about its device, if queryable in standalone.
    try:
        log(f"ogs device: {cmds.ogs(deviceInformation=True)}")
    except Exception as exc:
        log(f"ogs deviceInformation unavailable: {exc}")

    for name, code in FORMATS:
        prefix = os.path.join(OUT_DIR, f"diag_{name}")
        cmds.setAttr("defaultRenderGlobals.imageFormat", code)
        cmds.setAttr("defaultRenderGlobals.imageFilePrefix", prefix, type="string")
        log(f"--- ogsRender to {name} (format code {code}) ---")
        try:
            result = cmds.ogsRender(camera="sideCam1", width=960, height=540)
            log(f"ogsRender returned: {result}")
            # Maya resolves the prefix against the project images rule, so trust
            # the returned path rather than OUT_DIR.
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
            log(f"ogsRender raised:\n{traceback.format_exc()}")

    log("diagnostic completed without aborting")
    maya.standalone.uninitialize()


if __name__ == "__main__":
    sys.exit(main())

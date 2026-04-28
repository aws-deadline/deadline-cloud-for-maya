---
inclusion: manual
---

# Renderer Handler Architecture

This document describes the render handler pattern as implemented in the codebase. Use this when designing features that touch renderer-specific behavior.

## Handler Hierarchy

All render handlers live in `src/deadline/maya_adaptor/MayaClient/render_handlers/`.

```
DefaultMayaHandler          (base class — handles mayaSoftware, mayaHardware, mayaHardware2, mayaVector, file)
├── ArnoldHandler           (arnold)
├── VRayHandler             (vray)
├── RedshiftHandler         (redshift)
└── RenderManHandler        (renderman)
```

## Factory Function

`get_render_handler()` in `__init__.py` maps renderer strings to handler instances:

```python
def get_render_handler(renderer: str = "mayaSoftware") -> DefaultMayaHandler:
    if renderer == "arnold":
        return ArnoldHandler()
    elif renderer == "vray":
        return VRayHandler()
    elif renderer == "renderman":
        return RenderManHandler()
    elif renderer == "redshift":
        return RedshiftHandler()
    else:
        return DefaultMayaHandler()
```

Any renderer string not matching a specific handler falls through to `DefaultMayaHandler`.

## How Actions Are Dispatched

The dispatch chain works as follows:

1. `MayaAdaptor._populate_action_queue()` enqueues an `Action("renderer", {"renderer": "arnold"})` first.
2. `MayaClient.set_renderer()` receives this action, calls `get_render_handler()`, and merges the handler's `action_dict` into `self.actions`:
   ```python
   def set_renderer(self, renderer: dict):
       render_handler = get_render_handler(renderer["renderer"])
       self.actions.update(render_handler.action_dict)
   ```
3. All subsequent actions (scene_file, camera, start_render, etc.) are dispatched to the handler's methods via `action_dict`.

## DefaultMayaHandler action_dict

The base class registers these actions in `__init__`:

| Action Key | Method | Purpose |
|------------|--------|---------|
| `start_render` | `start_render` | Renders a frame via `maya.cmds.render()` |
| `camera` | `set_camera` | Stores camera name for rendering |
| `image_height` | `set_image_height` | Stores image height |
| `image_width` | `set_image_width` | Stores image width |
| `ocio_config_file` | `set_ocio_config_file` | Sets OCIO color management config path |
| `output_file_path` | `set_output_file_path` | Sets workspace images file rule |
| `output_file_prefix` | `set_output_file_prefix` | Stores output file prefix |
| `path_mapping` | `set_path_mapping` | Configures Maya dirmap rules |
| `project_path` | `set_project_path` | Opens Maya workspace |
| `render_layer` | `set_render_layer` | Sets render layer via `render_kwargs["layer"]` |
| `render_setup_include_lights` | `set_render_setup_include_lights` | Sets `renderSetup_includeAllLights` optionVar |
| `cache_pathmapping` | `set_cache_pathmapping` | Applies dirmap to `absoluteCacheName` attributes |
| `scene_file` | `set_scene_file` | Opens scene file, runs preMel |

## What Each Handler Overrides or Adds

### ArnoldHandler

**Adds to action_dict:**
- `error_on_arnold_license_fail` → `set_error_on_arnold_license_fail`: Sets `defaultArnoldRenderOptions.abortOnLicenseFail`

**Sets in `__init__`:**
- `self.render_kwargs["batch"] = True`

**Overrides:**
- `start_render`: Uses `maya.cmds.arnoldRender(**self.render_kwargs)` instead of `maya.cmds.render()`. Passes frame via `render_kwargs["seq"]` and camera via `render_kwargs["camera"]`. Supports region rendering via `defaultArnoldRenderOptions.regionMinX/MaxX/MinY/MaxY`. Forces `renderType=0` (image output, not .ass export). Ensures `log_verbosity >= 2` for progress reporting.
- `set_render_layer`: Uses `maya.cmds.editRenderLayerGlobals(currentRenderLayer=...)` instead of the base class's `render_kwargs["layer"]` approach.

### VRayHandler

**Adds to action_dict:** Nothing extra.

**Overrides:**
- `start_render`: Checks `maya.cmds.pluginInfo("vrayformaya", query=True, loaded=True)` before rendering. Creates `vraySettings` node if missing via `maya.mel.eval("vrayCreateVRaySettingsNode")`. Sets resolution on `vraySettings.width/height` (not `defaultResolution`). Forces `animType=2` (specific frames), `vrscene_render_on=1`, `vrscene_on=0`. Downgrades GPU engine from RTX (3) to CUDA (2). Disables distributed rendering. Supports region rendering via `vray vfbControl -setregion` MEL command (requires EXR output format). Renders via `maya.cmds.vrend(**self.render_kwargs)`.
- `set_output_file_prefix`: Also sets `vraySettings.fileNamePrefix` in addition to storing the prefix.
- `set_render_layer`: Uses `maya.cmds.editRenderLayerGlobals(currentRenderLayer=...)` like Arnold.

**Has a helper method:**
- `vraySettingsNodeExists()`: Checks for and optionally creates the `vraySettings` node.

### RedshiftHandler

**Adds to action_dict:** Nothing extra.

**Sets in `__init__`:**
- `self.render_kwargs["animation"] = True`
- `self.render_kwargs["render"] = True`
- `self.render_kwargs["batch"] = True`

**Overrides:**
- `start_render`: Sets frame via `defaultRenderGlobals.startFrame/endFrame` and `defaultRenderGlobals.animation=1`. Renders via `maya.cmds.rsRender(**self.render_kwargs)`. Does not support region rendering.
- `set_render_layer`: Uses `maya.cmds.editRenderLayerGlobals(currentRenderLayer=...)` like Arnold and V-Ray.

### RenderManHandler

**Adds to action_dict:** Nothing extra.

**Sets in `__init__`:**
- `self.render_layer = "defaultRenderLayer"` (stores layer name as instance attribute)

**Overrides:**
- `start_render`: Checks `maya.cmds.pluginInfo("RenderManForMaya.py", query=True, loaded=True)`. Uses `rfm2` module directly: `rfm2.render.RNDR.set_render_type(rfm2.render.RT_BATCH)`, `rfm2.render_with_renderman()`, `rfm2.render.frame(...)`. Passes frame and layer via the `rfm2.render.frame()` command string. Does not support region rendering.
- `set_render_layer`: Stores layer name in `self.render_layer` (used in `rfm2.render.frame()` command string) instead of using `render_kwargs` or `editRenderLayerGlobals`.
- `set_image_height`: Immediately calls `maya.cmds.setAttr("defaultResolution.height", ...)` instead of storing the value.
- `set_image_width`: Immediately calls `maya.cmds.setAttr("defaultResolution.width", ...)` instead of storing the value.

## Adaptor-Side Renderer Behavior

The `MayaAdaptor` (server side) also has renderer-specific logic:

### Arnold Pathmapping
When `renderer == "arnold"`, `_start_maya_client()` calls `_setup_arnold_pathmapping()` which:
- Creates a temp directory with a JSON file following Arnold's path mapping format (`{"mac": {...}, "linux": {...}, "windows": {...}}`)
- Sets `ARNOLD_PATHMAP` environment variable pointing to this file
- Cleaned up in `on_stop()` and `on_cleanup()` via `_cleanup_arnold_dir()`

### Progress Regex Patterns
Different renderers emit progress differently. The adaptor's `_get_regex_callbacks()` handles:
- General: `[PROGRESS] NN percent`
- Arnold: `NN% done`
- RenderMan: `R90000  NN%`

### License Error Handling
Separate error handlers exist for:
- Maya license: Checks `ADSKFLEX_LICENSE_FILE` and disk space
- V-Ray license: `"error: Could not obtain a license"`
- RenderMan license: `{SEVERE} License.*` pattern, checks `PIXAR_LICENSE_FILE` and `RMANTREE`
- Arnold license: Optional via `error_on_arnold_license_fail` init_data flag; matches `"aborting render because...abort_on_license_fail"`

## Supported Renderer Strings (from init_data.schema.json)

```json
"renderer": {
    "enum": [
        "arnold", "file", "mayaHardware", "mayaHardware2",
        "mayaSoftware", "mayaVector", "vray", "renderman", "redshift"
    ]
}
```

## Region Rendering Support

| Renderer | Region Rendering | Notes |
|----------|-----------------|-------|
| Arnold | Yes | Via `defaultArnoldRenderOptions.regionMinX/MaxX/MinY/MaxY` |
| V-Ray | Yes | Via `vray vfbControl -setregion` MEL; requires EXR output |
| Redshift | No | Not implemented |
| RenderMan | No | Not implemented |
| Maya Software | No | Raises RuntimeError if region specified |

## Render Command Summary

| Renderer | Render Command | Frame Mechanism |
|----------|---------------|-----------------|
| Maya Software | `maya.cmds.render(camera, **kwargs)` | `defaultRenderGlobals.startFrame/endFrame` |
| Arnold | `maya.cmds.arnoldRender(**kwargs)` | `render_kwargs["seq"] = frame` |
| V-Ray | `maya.cmds.vrend(**kwargs)` | `vraySettings.animFrames = str(frame)` |
| Redshift | `maya.cmds.rsRender(**kwargs)` | `defaultRenderGlobals.startFrame/endFrame` |
| RenderMan | `rfm2.render.frame(f" -s {frame} -e {frame} ...")` | Command string argument |

## Render Layer Mechanism

| Renderer | How Render Layer Is Set |
|----------|------------------------|
| Maya Software | `render_kwargs["layer"] = render_layer_name` |
| Arnold | `maya.cmds.editRenderLayerGlobals(currentRenderLayer=...)` |
| V-Ray | `maya.cmds.editRenderLayerGlobals(currentRenderLayer=...)` |
| Redshift | `maya.cmds.editRenderLayerGlobals(currentRenderLayer=...)` |
| RenderMan | Stored in `self.render_layer`, passed in `rfm2.render.frame()` string |

## Resolution Handling

| Renderer | Width/Height Set On |
|----------|---------------------|
| Maya Software | Stored in `self.image_width/height`, applied in `start_render` on `defaultResolution` |
| Arnold | Same as Maya Software |
| V-Ray | `vraySettings.width/height` (not `defaultResolution`) |
| Redshift | Same as Maya Software |
| RenderMan | `defaultResolution.width/height` set immediately in `set_image_width/height` |

## Action Queue Order

The adaptor enqueues init actions in this order:
1. `renderer` (always first — sets up the handler)
2. `path_mapping` (always second — configures dirmap)
3. `scene_file`, `project_path` (from `_FIRST_MAYA_ACTIONS`)
4. Remaining init_data keys from `_MAYA_INIT_KEYS` (camera, image_height, image_width, ocio_config_file, output_file_path, output_file_prefix, render_layer, render_setup_include_lights, cache_pathmapping, error_on_arnold_license_fail) — only if present in init_data

Then per-task:
5. `start_render` with run_data (frame, optional camera, optional region bounds, optional output_file_prefix)

---
inclusion: manual
---

# Renderer Handler Development Guide

How the render handler system works and how to modify or extend it.

## File Locations

```
src/deadline/maya_adaptor/MayaClient/render_handlers/
├── __init__.py                 # get_render_handler() factory
├── default_maya_handler.py     # Base class (DefaultMayaHandler)
├── arnold_handler.py           # ArnoldHandler
├── vray_handler.py             # VRayHandler
├── redshift_handler.py         # RedshiftHandler
└── renderman_handler.py        # RenderManHandler
```

Related files:
- `src/deadline/maya_adaptor/MayaClient/maya_client.py` — `MayaClient.set_renderer()` wires up the handler
- `src/deadline/maya_adaptor/MayaAdaptor/adaptor.py` — Server-side adaptor, enqueues actions
- `src/deadline/maya_adaptor/MayaAdaptor/schemas/init_data.schema.json` — Allowed renderer values
- `src/deadline/maya_adaptor/MayaAdaptor/schemas/run_data.schema.json` — Per-frame data schema

## How It Works

1. The adaptor enqueues `Action("renderer", {"renderer": "arnold"})` as the first action.
2. `MayaClient.set_renderer()` calls `get_render_handler("arnold")` which returns an `ArnoldHandler()`.
3. The handler's `action_dict` is merged into `MayaClient.actions` via `self.actions.update(render_handler.action_dict)`.
4. All subsequent actions (scene_file, camera, start_render, etc.) dispatch to the handler's methods.

## DefaultMayaHandler Base Class

The base class registers 13 actions in `self.action_dict`:

```
start_render, camera, image_height, image_width, ocio_config_file,
output_file_path, output_file_prefix, path_mapping, project_path,
render_layer, render_setup_include_lights, cache_pathmapping, scene_file
```

Instance state:
- `self.image_width` / `self.image_height` — stored, applied during `start_render`
- `self.camera_name` — stored by `set_camera`, used in `start_render`
- `self.output_file_prefix` — stored, applied during `start_render`
- `self.render_kwargs` — dict passed to the render command

Helper methods available to subclasses:
- `get_camera_to_render(data)` — validates camera exists and is renderable, returns camera name
- `get_render_layer_to_render(data)` — resolves display name to internal render layer name

## What Each Handler Changes

### ArnoldHandler

Adds one action: `error_on_arnold_license_fail`

Sets `render_kwargs["batch"] = True` in `__init__`.

Overrides `start_render`:
- Renders with `maya.cmds.arnoldRender(**self.render_kwargs)`
- Frame passed via `render_kwargs["seq"]`, camera via `render_kwargs["camera"]`
- Supports region rendering (`defaultArnoldRenderOptions.regionMinX/MaxX/MinY/MaxY`)
- Forces `defaultArnoldRenderOptions.renderType = 0` (image, not .ass)
- Ensures `log_verbosity >= 2` for progress output

Overrides `set_render_layer`:
- Uses `maya.cmds.editRenderLayerGlobals(currentRenderLayer=...)` instead of `render_kwargs["layer"]`

Adaptor-side: `_setup_arnold_pathmapping()` creates a JSON file for `ARNOLD_PATHMAP` env var.

### VRayHandler

No extra actions added.

Overrides `start_render`:
- Checks `pluginInfo("vrayformaya", loaded=True)` before rendering
- Creates `vraySettings` node if missing via `maya.mel.eval("vrayCreateVRaySettingsNode")`
- Resolution set on `vraySettings.width/height` (not `defaultResolution`)
- Forces `animType=2`, `vrscene_render_on=1`, `vrscene_on=0`
- Downgrades GPU engine from RTX (3) to CUDA (2)
- Disables distributed rendering
- Supports region rendering via `vray vfbControl -setregion` MEL (requires EXR output)
- Renders with `maya.cmds.vrend(**self.render_kwargs)`

Overrides `set_output_file_prefix`:
- Also sets `vraySettings.fileNamePrefix`

Overrides `set_render_layer`:
- Uses `editRenderLayerGlobals` like Arnold

Has helper: `vraySettingsNodeExists()` — checks/creates `vraySettings` node.

### RedshiftHandler

No extra actions added.

Sets in `__init__`:
- `render_kwargs["animation"] = True`
- `render_kwargs["render"] = True`
- `render_kwargs["batch"] = True`

Overrides `start_render`:
- Frame set via `defaultRenderGlobals.startFrame/endFrame` + `animation=1`
- Renders with `maya.cmds.rsRender(**self.render_kwargs)`
- No region rendering support

Overrides `set_render_layer`:
- Uses `editRenderLayerGlobals` like Arnold and V-Ray

### RenderManHandler

No extra actions added.

Sets `self.render_layer = "defaultRenderLayer"` in `__init__`.

Overrides `start_render`:
- Checks `pluginInfo("RenderManForMaya.py", loaded=True)`
- Uses `rfm2` module: `rfm2.render.RNDR.set_render_type(rfm2.render.RT_BATCH)`, `rfm2.render_with_renderman()`, `rfm2.render.frame(...)`
- No region rendering support

Overrides `set_render_layer`:
- Stores in `self.render_layer` (used in `rfm2.render.frame()` string)

Overrides `set_image_height` / `set_image_width`:
- Sets `defaultResolution` immediately instead of storing

## Adding a New Action to an Existing Handler

1. Add the method to the handler class:
   ```python
   def set_my_feature(self, data: dict) -> None:
       val = data.get("my_feature")
       maya.cmds.setAttr("someNode.someAttr", val)
   ```

2. Register it in the handler's `__init__`:
   ```python
   def __init__(self):
       super().__init__()
       self.action_dict["my_feature"] = self.set_my_feature
   ```

3. Add `"my_feature"` to `_MAYA_INIT_KEYS` in `adaptor.py` (if it's an init-time action):
   ```python
   _MAYA_INIT_KEYS = {
       ...existing keys...,
       "my_feature",
   }
   ```

4. Add the property to `init_data.schema.json`:
   ```json
   "my_feature": { "type": "string" }
   ```

5. Update `integration_data_interface_version` in `adaptor.py` (semver — bump minor for additions).

## Adding a New Renderer Handler

1. Create `src/deadline/maya_adaptor/MayaClient/render_handlers/new_handler.py`:
   ```python
   from .default_maya_handler import DefaultMayaHandler
   import maya.cmds

   class NewHandler(DefaultMayaHandler):
       def __init__(self):
           super().__init__()
           # Add renderer-specific render_kwargs
           # Register any extra actions

       def start_render(self, data: dict) -> None:
           # Implement renderer-specific render logic
           ...
   ```

2. Register in `__init__.py`:
   ```python
   from .new_handler import NewHandler

   def get_render_handler(renderer: str = "mayaSoftware") -> DefaultMayaHandler:
       ...
       elif renderer == "newrenderer":
           return NewHandler()
       ...
   ```

3. Add the renderer string to `init_data.schema.json`'s `renderer.enum` list.

4. Add progress regex patterns to `_get_regex_callbacks()` in `adaptor.py` if the renderer outputs progress differently.

5. Add license error handling in `_get_regex_callbacks()` if the renderer has specific license error patterns.

6. Update `integration_data_interface_version` in `adaptor.py`.

## Key Differences to Watch For

### Render commands
- Maya Software: `maya.cmds.render()`
- Arnold: `maya.cmds.arnoldRender()`
- V-Ray: `maya.cmds.vrend()`
- Redshift: `maya.cmds.rsRender()`
- RenderMan: `rfm2.render.frame()`

### Resolution nodes
- Most renderers: `defaultResolution.width/height`
- V-Ray: `vraySettings.width/height`

### Render layer mechanism
- Maya Software: `render_kwargs["layer"]`
- Arnold/V-Ray/Redshift: `maya.cmds.editRenderLayerGlobals(currentRenderLayer=...)`
- RenderMan: `self.render_layer` passed in command string

### Region rendering
- Arnold: `defaultArnoldRenderOptions.regionMinX/MaxX/MinY/MaxY`
- V-Ray: `vray vfbControl -setregion` MEL command (EXR only)
- Redshift/RenderMan/Maya Software: Not supported (raises RuntimeError)

### Plugin verification
- V-Ray: Checks `pluginInfo("vrayformaya", loaded=True)`
- RenderMan: Checks `pluginInfo("RenderManForMaya.py", loaded=True)`
- Arnold/Redshift/Maya Software: No explicit plugin check in handler

## Unit Testing Handlers

Handler tests mock `maya.cmds` and `maya.mel`. Existing test files:
```
test/unit/deadline/maya_adaptor/MayaClient/render_handlers/
```

Pattern:
```python
from unittest.mock import patch, MagicMock

@patch("deadline.maya_adaptor.MayaClient.render_handlers.arnold_handler.maya.cmds")
def test_arnold_start_render(self, mock_cmds):
    handler = ArnoldHandler()
    handler.start_render({"frame": 1, "camera": "persp"})
    mock_cmds.arnoldRender.assert_called_once()
```

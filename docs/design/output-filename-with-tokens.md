# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Output File Prefix Token System — Design Document

## Overview

This feature adds output file prefix token resolution to the Deadline Cloud for Maya submitter and adaptor. Users type the full `imageFilePrefix` pattern directly, with optional tokens that get resolved by the adaptor at render time.

**WYSIWYG principle:** The pattern is passed through exactly as the user types it. No automatic prepending of tokens, no automatic cleanup. What you see is what you get.

**Supported tokens:**

- `<Scene>` (alias: `%s`) — Scene file name without extension (e.g., "myScene")
- `<RenderLayer>` (aliases: `<Layer>`, `%l`) — Render layer display name (e.g., "masterLayer")
- `<Camera>` (alias: `%c`) — Camera name (e.g., "persp", "renderCam")

Token definitions are maintained in a single source of truth: `SUPPORTED_TOKENS` dict in `filename_utils.py`. The UI tooltip is generated from this dict via `get_tokens_tooltip()`, so adding a new token only requires updating one place.

Everything else in the pattern is literal text. Path separators (`/`) create subdirectories.

**All tokens are resolved by the adaptor at render time.** The submitter passes the raw pattern through to init-data. The adaptor already has all the data it needs: scene file path from init-data, render layer from init-data, and camera from run-data or init-data.

**Unknown tokens pass through unmodified.** Renderer-specific tokens like `<RenderPass>` are left for Maya or the renderer to handle.

**Token matching is case-insensitive.** Both `<Scene>` and `<scene>` resolve to the scene name.

**Example patterns and results:**

| Pattern | Scene=myScene, Layer=fg, Camera=renderCam |
|---------|-------------------------------------------|
| `<Scene>/<RenderLayer>/<RenderLayer>` | `myScene/fg/fg` |
| `<Scene>/<Camera>/<RenderLayer>` | `myScene/renderCam/fg` |
| `<Camera>/<Scene>` | `renderCam/myScene` |
| `<Scene>` | `myScene` |
| `myRender` | `myRender` |

**Default pattern initialization:**

1. Read `defaultRenderGlobals.imageFilePrefix` from the Maya scene
2. If empty, default to `<Scene>`
3. Sticky settings always take precedence — if the user previously saved a pattern, that loads instead

---

## 1. Data Structures

### 1.1 New field on `RenderSubmitterUISettings`

**File:** `src/deadline/maya_submitter/data_classes.py`

```python
@dataclass
class RenderSubmitterUISettings:
    ...existing fields...

    # Output file prefix pattern with optional tokens (<Scene>, <RenderLayer>, <Camera>).
    # Resolved by the adaptor at render time. Empty string means use scene default.
    output_file_prefix_pattern: str = field(default="", metadata={"sticky": True})
```

### 1.2 Shared utility functions

**File:** `src/deadline/maya_adaptor/MayaClient/filename_utils.py`

This file contains:

- `SUPPORTED_TOKENS` — single source of truth dict mapping canonical tokens to their aliases
- `get_tokens_tooltip()` — builds the UI tooltip string from `SUPPORTED_TOKENS`
- `resolve_tokens()` — case-insensitive token replacement with alias support

```python
SUPPORTED_TOKENS: dict[str, list[str]] = {
    "<Scene>": ["%s"],
    "<RenderLayer>": ["<Layer>", "%l"],
    "<Camera>": ["%c"],
}

def resolve_tokens(
    pattern: str,
    scene_name: str = "",
    render_layer: str = "",
    camera: str = "",
) -> str:
    """
    Replace supported tokens in a Maya imageFilePrefix pattern with actual values.
    Case-insensitive. Aliases included. Path structure (/) is preserved.
    Unknown tokens pass through unmodified.
    """
    ...
```

---

## 2. UX Changes (Submitter Dialog)

### 2.1 Output File Prefix pattern field

**File:** `src/deadline/maya_submitter/ui/components/scene_settings_tab.py`

A new "Output File Prefix" group box is added to the scene settings tab, containing the pattern input and a live preview:

```
Row 0: Project Path       [/path/to/project              ] [...]
Row 1: Output Path        [/path/to/output               ] [...]
Row 2: ┌─ Output File Prefix ────────────────────────────────────────┐
       │  Pattern    [<Scene>/<RenderLayer>/<RenderLayer>          ]  │
       │  Preview    myScene/masterLayer/masterLayer                  │
       └─────────────────────────────────────────────────────────────┘
Row 3: Render Layers      [All Renderable Layers          ▼]
Row 4: Cameras            [All Cameras                    ▼]
...
```

| Control | Type | Default | Sticky | Notes |
|---------|------|---------|--------|-------|
| Pattern | `QLineEdit` | Scene's `imageFilePrefix` or `<Scene>` | Yes | Tooltip generated from `SUPPORTED_TOKENS` |
| Preview | `QLabel` | (computed) | No | Read-only, updates when pattern or camera changes |

### 2.2 Default pattern initialization

**File:** `src/deadline/maya_submitter/maya_render_submitter.py`

The default pattern is read from the scene before sticky settings load:

```python
render_settings.output_file_prefix_pattern = get_base_output_prefix()
render_settings.load_sticky_settings(Scene.name())
```

This means:

- If `imageFilePrefix` = `<Scene>/<RenderLayer>/<RenderLayer>` → pattern = `<Scene>/<RenderLayer>/<RenderLayer>`
- If `imageFilePrefix` is empty → pattern = `<Scene>`
- If sticky settings exist → pattern = whatever the user last saved

### 2.3 Preview update logic

The preview updates whenever the pattern text or camera selection changes. It calls `resolve_tokens()` with the current scene name, a sample render layer name, and the selected camera.

### 2.4 No auto-prepend

The submitter does **not** automatically prepend `<Camera>` or `<RenderLayer>` tokens when they are missing. If the user omits tokens from a multi-camera or multi-layer render, the output files may overwrite each other — but that is the user's explicit choice.

---

## 3. Job Template and Bundle Changes

### 3.1 No changes to `default_maya_job_template.yaml`

The template stays as-is. The `OutputFilePrefix` parameter carries the raw pattern with unresolved tokens.

### 3.2 No changes to `init_data.schema.json` or `run_data.schema.json`

No new fields. The existing `output_file_prefix` field carries the raw pattern string.

### 3.3 Raw pattern passed through to job bundle

**File:** `src/deadline/maya_submitter/maya_render_submitter.py`

When the user sets a pattern in the UI, it overrides all layers' `output_file_prefix`:

```python
if settings.output_file_prefix_pattern:
    for layer_data in submit_render_layers:
        layer_data.output_file_prefix = settings.output_file_prefix_pattern
```

The raw pattern flows into the `OutputFilePrefix` job parameter and into each step's init-data as `output_file_prefix`.

---

## 4. Adaptor Changes

### 4.1 Token resolution in `DefaultMayaHandler`

**File:** `src/deadline/maya_adaptor/MayaClient/render_handlers/default_maya_handler.py`

A new `_resolve_output_file_prefix()` method resolves tokens using data available at render time:

```python
def _resolve_output_file_prefix(self, data: dict) -> Optional[str]:
    raw_prefix = data.get("output_file_prefix", self.output_file_prefix)
    if not raw_prefix:
        return raw_prefix

    scene_file = maya.cmds.file(query=True, sceneName=True)
    scene_name = os.path.splitext(os.path.basename(scene_file))[0]
    camera = data.get("camera", self.camera_name) or ""
    render_layer = ...  # from render_kwargs or editRenderLayerGlobals query
    render_layer = _get_render_layer_display_name(render_layer)

    return resolve_tokens(raw_prefix, scene_name=scene_name, render_layer=render_layer, camera=camera)
```

### 4.2 All renderer handlers updated

Each renderer handler's `start_render()` calls `_resolve_output_file_prefix()` instead of passing the raw prefix directly:

```python
# Before
output_file_prefix = data.get("output_file_prefix", self.output_file_prefix)

# After
output_file_prefix = self._resolve_output_file_prefix(data)
```

This applies to:

- `DefaultMayaHandler` (Maya Software)
- `ArnoldHandler`
- `VRayHandler`
- `RedshiftHandler`
- `RenderManHandler`

Token resolution is centralized in the base class. Renderer handlers inherit it.

---

## 5. Removed: Auto-Prepend Logic

**File:** `src/deadline/maya_submitter/renderers.py`

The previous `get_output_prefix_with_tokens()` function automatically prepended `<Camera>` and `<Layer>` tokens when multiple cameras or render layers were detected. This has been removed. The function now returns the scene's `imageFilePrefix` exactly as set.

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `src/deadline/maya_adaptor/MayaClient/filename_utils.py` | New. `SUPPORTED_TOKENS`, `get_tokens_tooltip()`, `resolve_tokens()` |
| `src/deadline/maya_adaptor/MayaClient/render_handlers/default_maya_handler.py` | `_resolve_output_file_prefix()` method; updated `start_render()` |
| `src/deadline/maya_adaptor/MayaClient/render_handlers/arnold_handler.py` | Uses `_resolve_output_file_prefix()` |
| `src/deadline/maya_adaptor/MayaClient/render_handlers/vray_handler.py` | Uses `_resolve_output_file_prefix()` |
| `src/deadline/maya_adaptor/MayaClient/render_handlers/redshift_handler.py` | Uses `_resolve_output_file_prefix()` |
| `src/deadline/maya_adaptor/MayaClient/render_handlers/renderman_handler.py` | Uses `_resolve_output_file_prefix()` |
| `src/deadline/maya_submitter/data_classes.py` | Add `output_file_prefix_pattern` sticky field |
| `src/deadline/maya_submitter/ui/components/scene_settings_tab.py` | "Output File Prefix" group box with pattern + live preview |
| `src/deadline/maya_submitter/maya_render_submitter.py` | Default pattern from scene; raw pattern passed to job bundle |
| `src/deadline/maya_submitter/renderers.py` | Removed auto-prepend logic |
| `test/unit/.../test_filename_utils.py` | Unit tests for `resolve_tokens()` |
| `test/unit/.../test_maya_handler_base.py` | Unit tests for `_resolve_output_file_prefix()` |

---
inclusion: manual
---

# Submitter Development Guide

How the submitter code is organized and how to modify it.

## Key Files

| File | Purpose |
|------|---------|
| `maya_render_submitter.py` | Main logic: `_get_job_template()`, `_get_parameter_values()`, `on_create_job_bundle_callback()` |
| `data_classes.py` | `RenderSubmitterUISettings` dataclass — all UI-bound settings |
| `scene.py` | `Scene` class (static methods reading Maya state), `Animation` class, `RendererNames` enum |
| `renderers.py` | `get_width()`, `get_height()`, `get_output_prefix_with_tokens()` |
| `cameras.py` | Camera enumeration helpers |
| `render_layers.py` | Render layer enumeration, `LayerSelection` enum |
| `assets.py` | `AssetIntrospector` for auto-detecting scene file references |
| `default_maya_job_template.yaml` | Base job template — modified at runtime by `_get_job_template()` |
| `ui/components/scene_settings_tab.py` | `SceneSettingsWidget` — Qt UI (QGridLayout) |

All paths relative to `src/deadline/maya_submitter/`.

## Submission Flow

```
show_maya_render_submitter()
  → _set_render_setting()           → RenderSubmitterUISettings
  → _set_render_layer_data()        → list[RenderLayerData] (one per renderable layer)
  → AssetIntrospector               → auto-detected file attachments
  → SubmitJobToDeadlineDialog       → calls on_create_job_bundle_callback on submit

on_create_job_bundle_callback()
  → _get_job_template()             → builds final template from default + layers + renderers
  → _get_parameter_values()         → collects all param values
  → writes template.yaml, parameter_values.yaml, asset_references.yaml
```

## Adding a New Setting

### 1. Data class field

In `data_classes.py`, add to `RenderSubmitterUISettings`:
```python
my_setting: bool = field(default=False, metadata={"sticky": True})
```
Use `metadata={"sticky": True}` if the value should persist across sessions.

### 2. UI widget

In `scene_settings_tab.py`, add in `_build_ui()`:
```python
self.my_setting_chck = QCheckBox("My Setting", self)
lyt.addWidget(self.my_setting_chck, ROW_NUMBER, 0)
```

Wire it in `_configure_settings()`:
```python
self.my_setting_chck.setChecked(settings.my_setting)
```

Read it in `update_settings()`:
```python
settings.my_setting = self.my_setting_chck.isChecked()
```

### 3. Job template parameter

In `_get_job_template()`, add a parameter definition:
```python
job_template["parameterDefinitions"].append({
    "name": "MySetting",
    "type": "STRING",
    "userInterface": {
        "control": "CHECK_BOX",
        "label": "My Setting",
        "groupLabel": "Maya Settings",
    },
    "default": "false",
    "allowedValues": ["true", "false"],
})
```

### 4. Init data

In the step loop in `_get_job_template()`, append to init data:
```python
init_data["data"] += "my_setting: {{Param.MySetting}}\n"
```

### 5. Parameter value

In `_get_parameter_values()`:
```python
parameter_values.append({
    "name": "MySetting",
    "value": "true" if settings.my_setting else "false",
})
```

### 6. Schema + handler

Add `"my_setting"` to `init_data.schema.json`, `_MAYA_INIT_KEYS` in `adaptor.py`, and the handler's `action_dict`. See **renderer-handlers.md**.

## Renderer-Conditional Features

Currently only Arnold has submitter-side specific logic:

```python
# In _get_job_template():
if "arnold" in renderers:
    job_template["parameterDefinitions"].append({...})

# In step init data:
if layer_data.renderer_name == "arnold":
    init_data["data"] += "error_on_arnold_license_fail: {{Param.ArnoldErrorOnLicenseFailure}}\n"

# In _get_parameter_values():
if "arnold" in renderers:
    parameter_values.append({"name": "ArnoldErrorOnLicenseFailure", "value": ...})
```

V-Ray, Redshift, and RenderMan have no submitter-side specific parameters. Their specific behavior is all in the adaptor-side render handlers.

## Renderer Package Requirements

In `show_maya_render_submitter()`, packages are added per renderer:

```python
rez_packages = f"mayaIO-{maya_version} deadline_cloud_for_maya"
conda_packages = f"maya={maya_version}.* maya-openjd={adaptor_version}.*"

if "arnold" in all_renderers:
    rez_packages += " mtoa"
    conda_packages += " maya-mtoa"
if "vray" in all_renderers:
    conda_packages += " maya-vray"
if "redshift" in all_renderers:
    conda_packages += " maya-redshift"
```

## Scene Class Quick Reference

All static methods on `Scene` in `scene.py`:

```python
Scene.name()                          # scene file path
Scene.renderer()                      # current renderer string
Scene.project_path()                  # workspace root
Scene.output_path()                   # images output dir
Scene.get_output_directories(l, c)    # output dirs for layer+camera
Scene.error_on_arnold_license_fail()  # Arnold abortOnLicenseFail
Scene.autotx()                        # Arnold auto-TX
Scene.use_existing_tiled_textures()   # Arnold existing TX
Scene.ocio_config_file()              # OCIO config path or None
Scene.ensure_arnold_options_loaded()  # creates defaultArnoldRenderOptions if needed
Scene.yeti_cache_files()              # Yeti cache file paths
```

## UI Layout

`SceneSettingsWidget` uses `QGridLayout(row, col)`:

| Row | Control |
|-----|---------|
| 0 | Project Path (FileSearchLineEdit) |
| 1 | Output Path (FileSearchLineEdit) |
| 2 | Render Layers (QComboBox: ALL / CURRENT) |
| 3 | Cameras (QComboBox, dynamic) |
| 4 | Override Frame Range (QCheckBox + QLineEdit) |
| 5 | Include Adaptor Wheels (QCheckBox, developer only) |
| 10 | Spacer |

New controls go at the next available row (6, 7, etc.). Row 10 is a spacer.

## Sticky Settings

Fields with `metadata={"sticky": True}` are saved to `<scene>.deadline_render_settings.json` alongside the scene file. Loaded on dialog open, saved on submit.

## Per-Layer Parameter Splitting

When multiple render layers have different values, the submitter creates per-layer parameters:
- Different frame ranges → `Layer1Frames`, `Layer2Frames` instead of `Frames`
- Different output prefixes → `Layer1OutputFilePrefix`, etc.
- Different resolutions → `Layer1ImageWidth`, `Layer1ImageHeight`, etc.

This is handled automatically in `on_create_job_bundle_callback()` by comparing values across layers.

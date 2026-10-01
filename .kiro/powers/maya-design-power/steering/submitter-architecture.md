---
inclusion: manual
---

# Submitter Architecture

This document describes the submitter-side code as implemented. Use this when designing features that add UI controls, job parameters, or modify the submission flow.

## File Map

| File | Purpose |
|------|---------|
| `src/deadline/maya_submitter/maya_render_submitter.py` | Main submission logic: builds job template, parameter values, creates bundle |
| `src/deadline/maya_submitter/data_classes.py` | `RenderSubmitterUISettings` dataclass — all UI settings |
| `src/deadline/maya_submitter/scene.py` | `Scene` and `Animation` classes — reads Maya scene state via `maya.cmds` |
| `src/deadline/maya_submitter/renderers.py` | Resolution and output prefix helpers |
| `src/deadline/maya_submitter/cameras.py` | Camera enumeration |
| `src/deadline/maya_submitter/render_layers.py` | Render layer enumeration and `LayerSelection` enum |
| `src/deadline/maya_submitter/assets.py` | Asset introspection for file attachments |
| `src/deadline/maya_submitter/default_maya_job_template.yaml` | Base job template YAML |
| `src/deadline/maya_submitter/ui/components/scene_settings_tab.py` | `SceneSettingsWidget` — Qt UI for scene settings |

## Submission Flow

```
show_maya_render_submitter()
  ├── _set_render_setting()          → RenderSubmitterUISettings
  ├── _set_render_layer_data()       → list[RenderLayerData]
  ├── AssetIntrospector.parse_scene_assets()  → auto-detected attachments
  └── Creates SubmitJobToDeadlineDialog with on_create_job_bundle_callback

on_create_job_bundle_callback()
  ├── _get_job_template()            → modifies default template per layers/renderers
  ├── _get_parameter_values()        → collects all parameter values
  └── Writes template.yaml, parameter_values.yaml, asset_references.yaml
```

## RenderSubmitterUISettings (data_classes.py)

The main settings dataclass. Fields with `metadata={"sticky": True}` persist across sessions via JSON sidecar files.

```python
@dataclass
class RenderSubmitterUISettings:
    submitter_name: str = "Maya"
    name: str = ""                          # sticky
    description: str = ""                   # sticky
    priority: int = 50                      # sticky
    initial_status: str = "READY"           # sticky
    max_failed_tasks_count: int = 20        # sticky
    max_retries_per_task: int = 5           # sticky
    max_worker_count: int = -1              # sticky (-1 = unlimited)
    override_frame_range: bool = False      # sticky
    frame_list: str = ""                    # sticky
    project_path: str = ""
    output_path: str = ""
    input_filenames: list[str] = []         # sticky
    input_directories: list[str] = []       # sticky
    output_directories: list[str] = []      # sticky
    render_layer_selection: LayerSelection = LayerSelection.ALL
    all_layer_selectable_cameras: list[str] = [ALL_CAMERAS]
    current_layer_selectable_cameras: list[str] = [ALL_CAMERAS]
    camera_selection: str = ALL_CAMERAS
    include_adaptor_wheels: bool = False    # sticky, developer option
```

To add a new setting: add a field here, wire it in `SceneSettingsWidget`, and use it in `_get_job_template()` / `_get_parameter_values()`.

## RenderLayerData (maya_render_submitter.py)

Per-layer data collected from the scene. Not a dataclass — uses class-level annotations.

```python
class RenderLayerData:
    name: str                                          # internal layer name
    display_name: str                                  # user-visible name
    renderer_name: str                                 # "arnold", "vray", etc.
    ui_group_label: str                                # "Layer X Settings (arnold renderer)"
    frames_parameter_name: Optional[str]               # per-layer frames param (if layers differ)
    frame_range: str                                   # frame range string
    renderable_camera_names: list[str]                 # cameras renderable in this layer
    output_directories: set[str]                       # output dirs for this layer
    output_file_prefix_parameter_name: Optional[str]   # per-layer prefix param (if layers differ)
    output_file_prefix: str                            # output prefix with tokens
    image_width_parameter_name: Optional[str]          # per-layer width param (if layers differ)
    image_height_parameter_name: Optional[str]         # per-layer height param (if layers differ)
    image_resolution: tuple[int, int]                  # (width, height)
```

## Scene Class (scene.py)

Static methods that read Maya scene state. Key methods:

| Method | Returns | Notes |
|--------|---------|-------|
| `Scene.name()` | Scene file path | `maya.cmds.file(query=True, sceneName=True)` |
| `Scene.renderer()` | Renderer string | `maya.cmds.getAttr("defaultRenderGlobals.currentRenderer")` |
| `Scene.project_path()` | Workspace root | `maya.cmds.workspace(query=True, rootDirectory=True)` |
| `Scene.output_path()` | Images output dir | Uses workspace `images` file rule |
| `Scene.get_output_directories(layer, camera)` | Output dirs | `maya.cmds.renderSettings(firstImageName=True, ...)` |
| `Scene.error_on_arnold_license_fail()` | bool | Reads `defaultArnoldRenderOptions.abortOnLicenseFail` |
| `Scene.autotx()` | bool | Arnold auto-TX setting |
| `Scene.use_existing_tiled_textures()` | bool | Arnold existing TX setting |
| `Scene.ocio_config_file()` | Optional[str] | OCIO config path if custom config is active |
| `Scene.ensure_arnold_options_loaded()` | None | Creates `defaultArnoldRenderOptions` via `mtoa.core.createOptions()` if needed |

### RendererNames Enum

```python
class RendererNames(Enum):
    mayaSoftware = "mayaSoftware"
    arnold = "arnold"
    vray = "vray"
    renderman = "renderman"
    redshift = "redshift"
```

## Default Job Template Structure

The base template in `default_maya_job_template.yaml` defines:

**Parameters:**
- `MayaSceneFile` (PATH, FILE, IN)
- `Frames` (STRING)
- `ProjectPath` (PATH, DIRECTORY, NONE)
- `OutputFilePath` (PATH, DIRECTORY, OUT)
- `RenderSetupIncludeLights` (STRING, CHECK_BOX, default "true")
- `StrictErrorChecking` (STRING, CHECK_BOX, default "false")
- `OCIOConfigFile` (PATH, FILE, IN, HIDDEN, default "")

**Step:** One `Render` step with:
- `stepEnvironments[0]` — Maya environment with `initData` embedded file
- `script` — run script with `runData` embedded file
- Init data template: `scene_file`, `project_path`, `output_file_path`, `render_setup_include_lights`, `strict_error_checking`, `ocio_config_file`
- Run data template: `frame: {{Task.Param.Frame}}`

## How _get_job_template() Modifies the Template

The function takes the default template and modifies it based on the submission:

1. **Per-layer parameters**: If layers have different frame ranges, output prefixes, or resolutions, creates per-layer parameters (e.g., `Layer1Frames`, `Layer1OutputFilePrefix`, `Layer1ImageWidth`).

2. **Camera parameter**: If a specific camera is selected (not ALL_CAMERAS), adds a `Camera` dropdown parameter. If ALL_CAMERAS, adds Camera as a task parameter dimension in the parameter space.

3. **Per-layer steps**: Replicates the default step once per render layer. Each step's init data gets `renderer:` and `render_layer:` prepended, plus `output_file_prefix`, `image_width`, `image_height`, `cache_pathmapping: true`.

4. **Arnold-specific**: If any layer uses Arnold, adds `ArnoldErrorOnLicenseFailure` checkbox parameter and appends `error_on_arnold_license_fail` to that step's init data.

5. **Adaptor wheels** (developer option): Merges `adaptor_override_environment.yaml` into the template.

## How _get_parameter_values() Works

Collects values for all parameters defined in the template:

- Scene file, frames (per-layer or global), output prefix (per-layer or global), resolution (per-layer or global)
- Camera (if specific camera selected)
- Project path, output path, render setup include lights
- OCIO config file (if present in scene)
- Arnold error on license fail (if Arnold is a renderer)
- Queue parameters (Rez/Conda packages)
- Adaptor wheel overrides (if developer option enabled)

## Renderer-Specific Submitter Behavior

### Package Requirements

In `show_maya_render_submitter()`, renderer-specific packages are added:

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

### Arnold-Specific Parameters

Arnold is the only renderer with submitter-side specific parameters:
- `ArnoldErrorOnLicenseFailure` — CHECK_BOX, added to job template
- Value read from `Scene.error_on_arnold_license_fail()` which checks `defaultArnoldRenderOptions.abortOnLicenseFail`
- `Scene.ensure_arnold_options_loaded()` is called to create `defaultArnoldRenderOptions` if it doesn't exist yet

### No V-Ray/Redshift/RenderMan Specific Parameters

Currently, no other renderer has submitter-side specific parameters or UI controls. All renderer-specific behavior is handled on the adaptor side via the render handlers.

## SceneSettingsWidget (UI)

Qt widget using `QGridLayout`. Current controls:

| Row | Widget | Type | Bound To |
|-----|--------|------|----------|
| 0 | Project Path | `FileSearchLineEdit` (directory) | `settings.project_path` |
| 1 | Output Path | `FileSearchLineEdit` (directory) | `settings.output_path` |
| 2 | Render Layers | `QComboBox` (ALL / CURRENT) | `settings.render_layer_selection` |
| 3 | Cameras | `QComboBox` (dynamic) | `settings.camera_selection` |
| 4 | Override Frame Range | `QCheckBox` + `QLineEdit` | `settings.override_frame_range`, `settings.frame_list` |
| 5 | Include Adaptor Wheels | `QCheckBox` (developer only) | `settings.include_adaptor_wheels` |

The widget uses `QGridLayout` with `(row, col)` positioning. New controls go at the next available row.

### Adding a New UI Control

1. Add field to `RenderSubmitterUISettings` in `data_classes.py`
2. Add widget in `SceneSettingsWidget._build_ui()` at the next row
3. Set initial value in `_configure_settings()`
4. Read value in `update_settings()`
5. Use the value in `_get_job_template()` and/or `_get_parameter_values()`

### Pattern for Renderer-Conditional UI

There is no existing pattern for showing/hiding controls based on renderer. The current UI does not change based on which renderer is active. Arnold-specific parameters are added to the job template in `_get_job_template()` based on the `renderers` set, not via UI controls.

## Adding a New Renderer-Specific Feature (End to End)

To add a feature that only applies to a specific renderer:

1. **Scene query**: Add a static method to `Scene` class to read the Maya attribute
2. **Data class** (optional): Add field to `RenderSubmitterUISettings` if it needs UI
3. **UI** (optional): Add widget to `SceneSettingsWidget` if user-configurable
4. **Job template**: In `_get_job_template()`, add parameter definition conditionally:
   ```python
   if "vray" in renderers:
       job_template["parameterDefinitions"].append({...})
   ```
5. **Init data**: Append to the step's init data string for matching layers:
   ```python
   if layer_data.renderer_name == "vray":
       init_data["data"] += "my_setting: {{Param.MySetting}}\n"
   ```
6. **Parameter values**: In `_get_parameter_values()`, add the value conditionally
7. **Schema**: Add property to `init_data.schema.json`
8. **Handler**: Add action to the renderer's handler (see renderer-handlers.md)
9. **Adaptor**: Add key to `_MAYA_INIT_KEYS` in `adaptor.py`

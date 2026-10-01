---
inclusion: manual
---

# Deadline Cloud for Maya Architecture Guide

This guide explains the architecture of the Deadline Cloud for Maya integration to help with design decisions.

## High-Level Architecture

```
+------------------------------------------------------------------+
|                        Maya (Artist Workstation)                 |
|  +------------------------------------------------------------+  |
|  |                    Submitter Dialog                        |  |
|  |  - Collects job settings from user                         |  |
|  |  - Reads scene information                                 |  |
|  |  - Creates job bundle                                      |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                              |
                              | Job Bundle (YAML + assets)
                              v
+------------------------------------------------------------------+
|                      AWS Deadline Cloud                          |
|  - Schedules jobs                                                |
|  - Distributes tasks to workers                                  |
|  - Manages job queues                                            |
+------------------------------------------------------------------+
                              |
                              | Task assignment
                              v
+------------------------------------------------------------------+
|                    Worker (Render Node)                          |
|  +------------------------------------------------------------+  |
|  |                   MayaAdaptor (Server)                     |  |
|  |  - Receives tasks from Deadline Cloud                      |  |
|  |  - Manages Maya process lifecycle                          |  |
|  |  - Sends actions to MayaClient                             |  |
|  +------------------------------------------------------------+  |
|                              |                                   |
|                              | Actions (JSON)                    |
|                              v                                   |
|  +------------------------------------------------------------+  |
|  |                      MayaClient                            |  |
|  |  - Runs inside Maya process (mayapy)                       |  |
|  |  - Executes actions via maya.cmds / maya.mel               |  |
|  |  - Handles renderer-specific logic                         |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

## Component Details

### 1. Submitter (`src/deadline/maya_submitter/`)

The submitter runs inside Maya on the artist's workstation.

**Key Directories:**
- `ui/` - Dialog UI components (PySide2/Qt)
- `maya_render_submitter.py` - Main submission logic
- `render_layers.py` - Render layer handling

**Plugin (`maya_submitter_plugin/`):**
- `plug-ins/DeadlineCloudForMaya.py` - Maya plugin entry point
- `scripts/` - MEL scripts for shelf and UI

**Responsibilities:**
- Display job submission dialog
- Collect user settings (renderer, frame range, cameras, layers)
- Analyze scene (file references, textures, assets)
- Create job bundle with template and assets
- Submit to Deadline Cloud

### 2. Job Bundle

The job bundle is a directory containing:
- `template.yaml` - Job template with parameters and steps
- `parameter_values.yaml` - User-provided parameter values
- `asset_references.yaml` - Scene files, textures, references

**Template Structure:**
```yaml
specificationVersion: jobtemplate-2023-09
name: "Maya Render"
parameterDefinitions:
  - name: MayaSceneFile
    type: PATH
    objectType: FILE
  - name: Frames
    type: STRING
  - name: RenderSetupIncludeLayers
    type: STRING
  # ... more parameters

steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - name: Frame
          type: INT
          range: "{{Param.Frames}}"
    script:
      actions:
        onRun:
          command: maya-openjd
          args: [daemon, run, ...]
```

### 3. MayaAdaptor (`src/deadline/maya_adaptor/MayaAdaptor/`)

The adaptor server runs on the worker node and manages the Maya process.

**Key Files:**
- `adaptor.py` - Main adaptor class (extends BaseAdaptor)
- `schemas/init_data.schema.json` - Init data schema
- `schemas/run_data.schema.json` - Run data schema

**Responsibilities:**
- Start/stop Maya process (mayapy)
- Send initialization actions (scene file, renderer, etc.)
- Send per-task actions (frame number, output path, camera)
- Handle errors and logging
- Manage path mapping

### 4. MayaClient (`src/deadline/maya_adaptor/MayaClient/`)

The MayaClient runs inside the Maya process and executes actions.

**Key Files:**
- `maya_client.py` - Main client class
- `render_handlers/` - Renderer-specific handlers

**Responsibilities:**
- Receive actions from adaptor server
- Execute maya.cmds / maya.mel commands
- Handle renderer-specific render settings
- Report progress and errors

### 5. Schema Versioning

The adaptor uses two JSON schema files to define the contract between submitter and adaptor:
- `init_data.schema.json` - Initialization data (once per job)
- `run_data.schema.json` - Per-task data (each frame/task)

**Important:** When modifying schemas, update `integration_data_interface_version` in `adaptor.py`.

## Data Flow: Submitter to Render

### 1. Job Submission

```
User fills dialog → Submitter creates bundle → Submit to Deadline Cloud
                         |
                         +-- template.yaml (job definition)
                         +-- parameter_values.yaml (user settings)
                         +-- asset_references.yaml
```

### 2. Task Execution

```
Deadline Cloud assigns task to worker
         |
         v
MayaAdaptor receives task
         |
         +-- Init actions (once per job):
         |   +-- scene_file: Load the .ma/.mb file
         |   +-- renderer: Set up renderer
         |   +-- render_layer: Set render layer
         |   +-- camera: Set camera
         |   +-- output_file_path: Set output directory
         |
         +-- Run actions (per frame):
             +-- frame: Set frame number
             +-- start_render: Execute render
```

## Adding a New Feature

### Step 1: Submitter Changes

1. Add UI controls to collect user input
2. Add parameters to job template
3. Write parameter values to bundle

### Step 2: Adaptor Changes

1. Read parameters from job bundle
2. Update schema files if needed
3. Create actions to send to MayaClient
4. Add to init_data or run_data as appropriate

### Step 3: MayaClient Changes

1. Add handler method for new action
2. Register action in handler's action_dict
3. Implement maya.cmds / maya.mel logic

## Path Mapping

Assets may be at different paths on worker vs. artist workstation.

**OpenJD provides:**
- Path mapping rules file
- `map_path()` function for translating paths

**Usage in handlers:**
```python
# Path mapping is handled by the adaptor framework
# Scene file paths are automatically mapped
```

## Testing Strategy

1. **Unit tests** (`test/unit/`): Mock maya.cmds, test handler logic
2. **Integration tests** (`test/integ/`): Test with real Maya (mayapy)
3. **Job bundle output tests** (`job_bundle_output_tests/`): Validate generated bundles via Maya TEST button

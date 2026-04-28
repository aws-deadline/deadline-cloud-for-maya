---
inclusion: manual
---

# Research Guide for Maya Designs

This guide covers how to research and validate design decisions for Maya and renderer features.

## Maya Documentation Sources

### Official Autodesk Documentation

1. **Maya Python Command Reference (maya.cmds)**
   - URL: https://help.autodesk.com/view/MAYAUL/2026/ENU/?guid=__CommandsPython_index_html
   - Covers: All maya.cmds commands, flags, and return values

2. **Maya Python API 2.0 (OpenMaya)**
   - URL: https://help.autodesk.com/view/MAYAUL/2026/ENU/?guid=Maya_SDK_py_ref_index_html
   - Covers: OpenMaya module, MFn classes, MIt iterators

3. **MEL Command Reference**
   - URL: https://help.autodesk.com/view/MAYAUL/2026/ENU/?guid=__Commands_index_html
   - Covers: All MEL commands (many map directly to maya.cmds)

4. **Maya Technical Documentation**
   - URL: https://help.autodesk.com/view/MAYAUL/2026/ENU/?guid=GUID-F9201B97-7B04-4B60-B4B5-A9B589AC5B3C
   - Covers: Nodes, attributes, dependency graph

### Arnold (MtoA) Documentation

1. **Arnold for Maya User Guide**
   - URL: https://help.autodesk.com/view/ARNOL/ENU/?guid=arnold_for_maya_install_Install_MtoA_html
   - Covers: Installation, render settings, AOVs, shaders

2. **Arnold Python API**
   - Key nodes: `defaultArnoldRenderOptions`, `defaultArnoldDriver`, `defaultArnoldFilter`
   - AOV management: `cmds.arnoldRenderView()`, `cmds.arnoldListAOVs()`

### V-Ray for Maya Documentation

1. **V-Ray for Maya**
   - URL: https://docs.chaos.com/display/VMAYA
   - Covers: Render settings, V-Ray nodes, scripting

### Redshift for Maya Documentation

1. **Redshift for Maya**
   - URL: https://help.maxon.net/r3d/maya/en-us/
   - Covers: Render settings, AOVs, proxy objects

## Key Maya Python Patterns

### Renderer Detection

```python
import maya.cmds as cmds

# Get current renderer
renderer = cmds.getAttr('defaultRenderGlobals.currentRenderer')
# Returns: 'arnold', 'vray', 'redshift', 'mayaSoftware', 'mayaHardware2'
```

### Scene Information

```python
import maya.cmds as cmds

# Current scene file
scene_file = cmds.file(q=True, sn=True)

# Scene modified state
is_modified = cmds.file(q=True, modified=True)

# All cameras
cameras = cmds.ls(type='camera')
renderable_cameras = [c for c in cameras if cmds.getAttr(f'{c}.renderable')]

# All render layers
render_layers = cmds.ls(type='renderLayer')
```

### Render Settings Access

```python
import maya.cmds as cmds

# Frame range
start_frame = cmds.getAttr('defaultRenderGlobals.startFrame')
end_frame = cmds.getAttr('defaultRenderGlobals.endFrame')
by_frame = cmds.getAttr('defaultRenderGlobals.byFrameStep')

# Resolution
width = cmds.getAttr('defaultResolution.width')
height = cmds.getAttr('defaultResolution.height')

# Output path
output_prefix = cmds.getAttr('defaultRenderGlobals.imageFilePrefix')
```

### Arnold-Specific Settings

```python
import maya.cmds as cmds

# Arnold render settings
samples = cmds.getAttr('defaultArnoldRenderOptions.AASamples')
ray_depth = cmds.getAttr('defaultArnoldRenderOptions.GITotalDepth')

# Arnold AOVs
aovs = cmds.ls(type='aiAOV')
for aov in aovs:
    aov_name = cmds.getAttr(f'{aov}.name')
    aov_enabled = cmds.getAttr(f'{aov}.enabled')
```

### V-Ray-Specific Settings

```python
import maya.cmds as cmds

# V-Ray render settings (via vraySettings node)
if cmds.objExists('vraySettings'):
    width = cmds.getAttr('vraySettings.width')
    height = cmds.getAttr('vraySettings.height')
    
    # V-Ray output
    save_file = cmds.getAttr('vraySettings.imageFormatStr')
```

### Redshift-Specific Settings

```python
import maya.cmds as cmds

# Redshift render settings
if cmds.objExists('redshiftOptions'):
    samples_min = cmds.getAttr('redshiftOptions.unifiedMinSamples')
    samples_max = cmds.getAttr('redshiftOptions.unifiedMaxSamples')
```

### File References and Assets

```python
import maya.cmds as cmds

# All file references
references = cmds.file(q=True, reference=True)

# All file texture nodes
file_nodes = cmds.ls(type='file')
for node in file_nodes:
    texture_path = cmds.getAttr(f'{node}.fileTextureName')

# XGen descriptions
xgen_descriptions = cmds.ls(type='xgmDescription')
```

## Maya Adaptor Architecture

### Adaptor Server-Client Pattern

The Maya adaptor follows the OpenJD adaptor pattern:
1. **MayaAdaptor** (server) - Manages Maya process lifecycle
2. **MayaClient** (client) - Runs inside Maya, executes commands via maya.cmds/mel

### Schema Files

- `src/deadline/maya_adaptor/MayaAdaptor/schemas/init_data.schema.json` - Initialization data
- `src/deadline/maya_adaptor/MayaAdaptor/schemas/run_data.schema.json` - Per-task data

### Action Flow

```
Submitter → Job Bundle → Deadline Cloud → Adaptor Server → MayaClient → maya.cmds
```

## Internet Research Guidelines

### When to Search

1. Documentation is unclear or incomplete
2. Looking for version-specific behavior
3. Finding community workarounds
4. Verifying API behavior across renderers

### Effective Search Queries

- `"maya.cmds" "[command]" site:help.autodesk.com`
- `"Arnold Maya" "[feature]" site:help.autodesk.com`
- `"V-Ray Maya" "[feature]" site:docs.chaos.com`
- `"Redshift Maya" "[feature]" site:help.maxon.net`
- `"maya python" "[topic]" site:stackoverflow.com`

## Knowledge Gap Protocol

When you encounter a knowledge gap:

1. **Document what you know**
   - What API/feature is involved?
   - What have you found so far?
   - What specific information is missing?

2. **Ask the user clearly**
   > "I need clarification on [topic]. Specifically:
   > - [Question 1]
   > - [Question 2]
   > 
   > Do you have documentation or code examples for this?"

3. **Propose alternatives if possible**
   > "I'm not certain about [X], but based on [Y], I believe we could:
   > - Option A: [description]
   > - Option B: [description]
   > 
   > Which approach would you prefer, or do you have more information?"

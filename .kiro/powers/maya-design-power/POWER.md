---
name: "maya-design-power"
displayName: "Maya Design Power"
description: "Structured design assistant for Maya features in Deadline Cloud. Creates comprehensive design documents covering data structures, UX changes, job templates, and adapter modifications."
keywords: ["maya", "design", "python", "arnold", "vray", "redshift", "mel", "cmds"]
author: "AWS Deadline Cloud Team"
---

# Maya Design Power

## Overview

A structured design assistant for creating comprehensive feature designs for Maya integration with AWS Deadline Cloud. This power helps create well-structured design documents following a consistent four-section format that covers all aspects of implementation.

## Code Snippet Style Guide

When including code in design documents, use **concise inline snippets** in the main sections and put **full implementations in an appendix**.

### Inline Code Format

Show only the relevant changes with context:

```python
def existing_function():
    ...existing logic...
    
    # NEW: Add feature X support
    if feature_x_enabled:
        self._configure_feature_x(data)
    
    ...rest of function...
```

### Appendix Format

Put complete implementations in a clearly marked appendix section:

```markdown
---

## Appendix: Full Code Implementations

<!-- REVIEW: New render handler implementation -->

### A.1 MayaHandler.configure_render (Full Implementation)

\`\`\`python
def configure_render(self, data: dict) -> None:
    """Full implementation here..."""
    # Complete code
\`\`\`
```

### Guidelines

1. **Data structures are the exception**: Always show full definitions - they anchor the design
2. **Other sections**: Show what changes and where, not full implementations
3. **Use `...` or comments** to indicate existing/unchanged code
4. **Flag new sections** with `<!-- REVIEW: description -->` comments in the appendix
5. **Don't include review tags** in final generated code

## MCP Tools

This power includes the **Autodesk Product Help MCP** server (`autodesk-product-help`), which provides direct access to Autodesk's official documentation for 110+ products including Maya, Arnold, and MEL.

Use it to:
- Research Maya Python API (maya.cmds, maya.mel, pymel) during design work
- Look up Arnold/V-Ray/Redshift render settings and parameters
- Find official Autodesk documentation for feature design references

The server exposes two tools:
- `get_available_products` - List all supported Autodesk products and their release codes
- `search_help_content` - Search Autodesk documentation by product, release, and query

When searching, use product code `MAYA` for Maya documentation.

## Research Requirements

Before finalizing any design, research Maya Python APIs, renderer-specific APIs, and internet sources. Use the Autodesk Product Help MCP to look up official documentation. Refer to **research-guide.md** for details.

## Renderer Handler Architecture

Refer to **renderer-handlers.md** for the full render handler class hierarchy, action dispatch flow, per-renderer differences (render commands, resolution nodes, render layer mechanisms, region rendering support), and how to design new actions or handlers.

## Submitter Architecture

Refer to **submitter-architecture.md** for the submission flow, data classes (`RenderSubmitterUISettings`, `RenderLayerData`), job template generation, parameter values, the `Scene` class, the `SceneSettingsWidget` UI, and the end-to-end pattern for adding renderer-specific features.

## Key Technical Patterns

Refer to **research-guide.md** for maya.cmds patterns, renderer detection, and settings access.

## External References

Refer to **external-references.md** for GitHub discussions and documentation links.

## Maya-Specific Considerations

### Maya Python API (maya.cmds / maya.mel)
- Scene access: `cmds.ls()`, `cmds.file(q=True, sn=True)`
- Render settings: `cmds.getAttr('defaultRenderGlobals.currentRenderer')`
- File paths: `cmds.workspace(q=True, rd=True)` for workspace root
- MEL evaluation: `maya.mel.eval('command')`

### Render Engines
- **Arnold (MtoA)**: `cmds.getAttr('defaultRenderGlobals.currentRenderer')` returns `'arnold'`
- **V-Ray**: Returns `'vray'`
- **Redshift**: Returns `'redshift'`
- **Maya Software**: Returns `'mayaSoftware'`
- **Maya Hardware 2.0**: Returns `'mayaHardware2'`

### Plugin Structure
- Maya module: `.mod` file in `MAYA_MODULE_PATH`
- Plugin: `DeadlineCloudForMaya.py` loaded via Plug-in Manager
- Shelf: AWSDeadline shelf with submit and test buttons
- Registration: `maya.api.OpenMaya.MFnPlugin`

### Job Submission Patterns
- Scene file handling: `.ma` (ASCII) and `.mb` (binary) files
- Asset references: Textures, caches, references, XGen
- Output paths: Frame sequences, render layers, AOVs
- Frame ranges: `cmds.getAttr('defaultRenderGlobals.startFrame')`, `cmds.getAttr('defaultRenderGlobals.endFrame')`

---
inclusion: manual
---

# Maya Design Workflow Guide

This guide walks through creating a comprehensive design document for a new Maya feature.

## Step 1: Understand the Feature Request

Before starting the design:
1. Clarify the user's goal and expected outcome
2. Identify which renderers are affected (Arnold, V-Ray, Redshift, Maya Software)
3. Determine if this is a new feature or modification to existing behavior
4. Ask clarifying questions if the scope is unclear

## Step 2: Research Phase

### 2.1 Search Maya Documentation

Look up relevant maya.cmds, maya.mel, and OpenMaya APIs:
- Command names and flags
- Node attributes and types
- Renderer-specific settings
- Version-specific differences (Maya 2024-2026)

Key search terms:
- "maya.cmds [command name]"
- "Maya Python API [topic]"
- "Arnold Maya [feature]"
- "V-Ray Maya [feature]"
- "Redshift Maya [feature]"

### 2.2 Check Existing Implementation

Review the current codebase:
- How does the submitter handle similar features?
- What patterns does the adaptor use?
- How are renderer-specific settings managed?

### 2.3 Internet Research

Search for:
- Community solutions and workarounds
- Known issues and limitations
- Version compatibility notes
- Best practices

## Step 3: Design the Data Structures

Data structures anchor the design - **always include full definitions** for new types:

```python
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum

class FeatureMode(Enum):
    """Mode options for Feature X."""
    OPTION_A = "option_a"
    OPTION_B = "option_b"

@dataclass
class FeatureSettings:
    """Settings for Feature X workflow."""
    
    enabled: bool = False
    mode: FeatureMode = FeatureMode.OPTION_A
    output_path: Optional[str] = None
    
    # Processing options
    compress_output: bool = True
    verbose_level: int = 3
```

Consider:
- What data flows from submitter to adaptor?
- What state needs to be maintained during rendering?
- What types should be used?

**Note:** Data structures are the exception to the "concise snippets" rule - show them in full since they anchor the entire design.

## Step 4: Design the UX

Sketch out the submitter dialog changes:

1. **Control Type**: Dropdown, checkbox, text field, etc.
2. **Placement**: Which group/section does it belong to?
3. **Default Value**: What's the sensible default?
4. **Validation**: What values are valid?
5. **Dependencies**: Does it depend on other settings?

Example:
```
Group: Renderer Settings
├── [Checkbox] Enable Feature X (default: unchecked)
│   └── [Dropdown] Feature X Mode (visible when enabled)
│       ├── Option A
│       └── Option B
└── [Text Field] Custom Path (optional)
```

## Step 5: Design Job Template Changes

Define the job bundle modifications:

```yaml
parameterDefinitions:
  - name: FeatureXEnabled
    type: STRING
    default: "false"
    allowedValues: ["true", "false"]
    
  - name: FeatureXMode
    type: STRING
    default: "option_a"
    allowedValues: ["option_a", "option_b"]
    userInterface:
      control: DROPDOWN
      label: "Feature X Mode"
```

Consider:
- Parameter types and constraints
- Conditional parameters
- Asset references

## Step 6: Design Adaptor Changes

Plan the runtime implementation using **concise inline snippets** that show what changes:

### Handler Changes (Inline)
```python
class MayaHandler:
    def __init__(self) -> None:
        super().__init__()
        ...existing init...
        
        # NEW: Register feature X action
        self.action_dict["feature_x"] = self.configure_feature_x

    def configure_feature_x(self, data: dict[str, Any]) -> None:
        """Configure Feature X before rendering."""
        # See Appendix A.1 for full implementation
        ...
```

### maya.cmds Implementation (Inline)
```python
def _apply_feature_x(self, mode: str) -> None:
    import maya.cmds as cmds
    
    renderer = cmds.getAttr('defaultRenderGlobals.currentRenderer')
    
    # NEW: Set feature X attribute
    if renderer == 'arnold':
        cmds.setAttr('defaultArnoldRenderOptions.featureX', mode)
```

Put full implementations in the **Appendix** section with review flags.

## Step 7: Plan Testing

Define unit tests with mocked maya.cmds:

```python
@patch('deadline.maya_adaptor.MayaClient.maya_handler.cmds')
def test_feature_x_configuration(self, mock_cmds):
    """Test Feature X is correctly configured."""
    # Setup
    handler = MayaHandler()
    
    # Execute
    handler.configure_feature_x({"feature_x_enabled": True, "feature_x_mode": "option_a"})
    
    # Verify
    mock_cmds.setAttr.assert_called_with('defaultArnoldRenderOptions.featureX', 'option_a')
```

## Step 8: Document Files to Modify

Create a summary table:

| File | Changes |
|------|---------|
| `src/deadline/maya_submitter/...` | Add UI controls |
| `maya_submitter_plugin/...` | Plugin changes |
| `src/deadline/maya_adaptor/MayaAdaptor/...` | Add adaptor logic |
| `src/deadline/maya_adaptor/MayaClient/...` | Add handler method |
| `test/unit/.../test_handler.py` | Add unit tests |

## Common Pitfalls

1. **Forgetting renderer differences**: Arnold, V-Ray, and Redshift have different APIs
2. **Missing type annotations**: All code needs proper types
3. **Hardcoded paths**: Use path mapping for cross-platform support
4. **No error handling**: maya.cmds operations can fail
5. **Untested edge cases**: Test with missing/invalid data
6. **Maya version differences**: Test across Maya 2024-2026

## Step 9: Create the Appendix

Put all full code implementations in a clearly marked appendix at the end of the design document.

### Appendix Format

```markdown
---

## Appendix: Full Code Implementations

<!-- REVIEW: Brief description of what's new -->

### A.1 ClassName.method_name (Full Implementation)

**File:** `src/deadline/maya_adaptor/...`

\`\`\`python
def method_name(self, data: dict) -> None:
    """
    Full docstring here.
    """
    # Complete implementation
    ...
\`\`\`

### A.2 New Utility Module

**File:** `src/deadline/maya_submitter/new_utils.py` (new file)

\`\`\`python
"""
Module docstring.
"""
# Full module code
\`\`\`
```

### Guidelines

1. **Flag sections for review** with `<!-- REVIEW: description -->` HTML comments
2. **Include file paths** for each code block
3. **Number appendix sections** (A.1, A.2, etc.) for easy reference
4. **Don't include review tags** in final generated code - they're for design review only
5. **Reference appendix from main sections** with "See Appendix A.X for full implementation"

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""
Shared output filename utilities for Deadline Cloud Maya integration.
Provides token-based output filename prefix resolution.

Supported tokens are resolved by the adaptor at render time.
Unknown tokens (e.g., renderer-specific ones like <RenderPass>) pass through
unmodified for Maya or the renderer to handle.
"""
import re

SUPPORTED_TOKENS: dict[str, list[str]] = {
    "<Scene>": ["%s"],
    "<RenderLayer>": ["<Layer>", "%l"],
    "<Camera>": ["%c"],
}


def get_tokens_tooltip() -> str:
    """Build a tooltip string describing all supported tokens."""
    lines: list[str] = ["Available tokens:"]
    for token, aliases in SUPPORTED_TOKENS.items():
        alias_str: str = f" (aliases: {', '.join(aliases)})" if aliases else ""
        lines.append(f"  {token}{alias_str}")
    lines.append("")
    lines.append("Everything else is literal text.")
    lines.append("Path separators (/) create subdirectories.")
    lines.append("Examples:")
    lines.append("  <Scene>/<RenderLayer>/<RenderLayer>")
    lines.append("  <Scene>/<Camera>/<RenderLayer>")
    lines.append("  <Scene>")
    return "\n".join(lines)


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
    if not pattern:
        return pattern

    replacements: dict[str, str] = {
        "<Scene>": scene_name,
        "%s": scene_name,
        "<RenderLayer>": render_layer,
        "<Layer>": render_layer,
        "%l": render_layer,
        "<Camera>": camera,
        "%c": camera,
    }

    result: str = pattern
    for token, value in replacements.items():
        result = re.sub(re.escape(token), value, result, flags=re.IGNORECASE)
    return result

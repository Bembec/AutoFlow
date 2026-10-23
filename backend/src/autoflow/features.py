"""
Feature flags: switch features on or off without a deploy.

A flag's value is decided in this order:
1. a per-workspace override set by staff (e.g. a design partner trying
   something new, or switching a feature off for one customer);
2. the AUTOFLOW_FEATURES environment variable, e.g.
   "smarter_logic=on,ai_builder=off" (per environment: staging can test
   what production doesn't have yet);
3. the default below.

New, unfinished work ships behind a flag that is off by default, so it can
be merged and tested in staging without customers seeing it.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Flag:
    default: bool
    description: str


FLAGS = {
    "ai_builder": Flag(True, "Draft workflows from plain words with AI."),
    "insights_suggestions": Flag(True, "Suggestions for what to automate or fix next on Insights."),
    "connection_checks": Flag(True, "The Check connection button on Connected apps."),
    "help_assistant": Flag(True, "Ask the help assistant (answers only from the help articles)."),
    "smarter_logic": Flag(False, "Comparisons, AND/OR conditions and for-each loops (in development)."),
    "mcp_tools": Flag(False, "Connect MCP servers and use their tools in workflows (in development)."),
}

ON = {"1", "true", "on", "yes"}
OFF = {"0", "false", "off", "no"}


class UnknownFlag(ValueError):
    pass


def _environment():
    values = {}
    for part in os.getenv("AUTOFLOW_FEATURES", "").split(","):
        name, _, value = part.strip().partition("=")
        if name in FLAGS and value.strip().lower() in ON | OFF:
            values[name] = value.strip().lower() in ON
    return values


def all_flags(workspace=None):
    """Every flag's current value for a workspace (or the environment)."""
    values = {name: flag.default for name, flag in FLAGS.items()}
    values.update(_environment())
    overrides = (workspace.feature_flags or {}) if workspace is not None else {}
    values.update({name: bool(value) for name, value in overrides.items() if name in FLAGS})
    return values


def enabled(name, workspace=None):
    if name not in FLAGS:
        raise UnknownFlag(name)
    return all_flags(workspace)[name]


def set_overrides(workspace, changes):
    """Apply {flag: True|False|None}; None removes the override."""
    unknown = [name for name in changes if name not in FLAGS]
    if unknown:
        raise UnknownFlag(", ".join(unknown))
    overrides = dict(workspace.feature_flags or {})
    for name, value in changes.items():
        if value is None:
            overrides.pop(name, None)
        else:
            overrides[name] = bool(value)
    # A new dict so SQLAlchemy notices the JSON change
    workspace.feature_flags = overrides or None

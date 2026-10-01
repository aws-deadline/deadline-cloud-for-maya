from deadline.client.ui.dataclasses.timeouts import TimeoutTableEntries

from typing import Any


def add_timeouts_to_job_template(template: dict[str, Any], timeouts: TimeoutTableEntries) -> None:
    """
    The job template may have multiple steps (one per render take).
    Each step has 1 task run and 1 environment with 3 actions:
    - Task run
    - Maya launch (onEnter)
    - Maya shutdown (onExit)
    We apply the timeouts to all steps.
    """
    timeouts.validate_entries()
    for step in template["steps"]:
        if timeouts.entries["Task Run"].is_activated:
            step["script"]["actions"]["onRun"]["timeout"] = timeouts.entries["Task Run"].seconds

        if timeouts.entries["Maya Launch"].is_activated:
            step["stepEnvironments"][0]["script"]["actions"]["onEnter"]["timeout"] = (
                timeouts.entries["Maya Launch"].seconds
            )

        if timeouts.entries["Maya Shutdown"].is_activated:
            step["stepEnvironments"][0]["script"]["actions"]["onExit"]["timeout"] = (
                timeouts.entries["Maya Shutdown"].seconds
            )

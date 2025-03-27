import os
from typing import Tuple

import click


def parse_agent_name(agent: str) -> Tuple[str, str]:
    """Parse agent name into base name and version.

    Args:
        agent: Agent name in format 'name:version'

    Returns:
        Tuple of (base_name, version)
    """
    if ":" not in agent:
        raise click.ClickException("Agent name must be in format 'name:version'")
    base_name, version = agent.split(":", 1)
    return base_name, version


def get_agent_dir(agent: str) -> str:
    """Get the agent directory path based on the agent name.

    Args:
        agent: Agent name in format 'name:version'

    Returns:
        Path to the agent directory
    """
    base_name, version = parse_agent_name(agent)
    return os.path.join(os.getcwd(), base_name, version)

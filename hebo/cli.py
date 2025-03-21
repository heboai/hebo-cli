import os
import shutil
from typing import List, Dict, Any, Optional, cast

import click
import requests
import yaml

from .config import save_profile, get_token, get_deployment_url


@click.group()
@click.version_option(package_name="hebo-cli")
def main():
    pass


@main.command()
def config():
    """Configure the CLI with a profile, deployment URL, and token."""
    profile_name = click.prompt("Enter profile name", type=str, default="default")
    deployment_url = click.prompt(
        "Enter deployment URL", type=str, default="https://app.hebo.ai"
    )

    # Validate deployment URL format
    if not deployment_url.startswith(("http://", "https://")):
        deployment_url = f"https://{deployment_url}"

    token = click.prompt("Enter token", type=str, hide_input=True)

    save_profile(profile_name, deployment_url, token)
    click.echo(f"Profile '{profile_name}' configured successfully")


@main.command()
@click.option("--profile", "-p", default="default", help="Profile name to use")
@click.argument("agent")
def pull(profile, agent):
    """Fetch data from the API using the specified profile and save it to the local filesystem."""
    token = get_token(profile)
    deployment_url = get_deployment_url(profile)

    if not token or not deployment_url:
        click.echo(f"Profile '{profile}' not found. Please hebo config it first.")
        return

    headers = {"X-API-Key": token}

    def _make_request(url) -> Optional[List[Dict[str, Any]]]:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                click.echo(f"Failed to get {url}")
                return None
        except requests.exceptions.RequestException as e:
            click.echo(f"Error connecting to deployment URL: {str(e)}")
            return None

    # Create or handle agent directory
    agent_dir = os.path.join(os.getcwd(), agent)
    if os.path.exists(agent_dir):
        if click.confirm(
            f"Directory '{agent}' already exists. Do you want to delete it and recreate?"
        ):
            shutil.rmtree(agent_dir)
        else:
            click.echo("Operation cancelled.")
            return

    os.makedirs(agent_dir, exist_ok=True)

    # Show progress while fetching data
    with click.progressbar(length=3, label="Fetching data") as bar:
        knowledge = _make_request(
            f"{deployment_url}/api/knowledge/?agent_version={agent}"
        )
        bar.update(1)
        tools = _make_request(f"{deployment_url}/api/tools/?agent_version={agent}")
        bar.update(1)
        agent_settings = _make_request(
            f"{deployment_url}/api/agent-settings/?agent_version={agent}"
        )
        bar.update(1)

    if knowledge is None or agent_settings is None:
        click.echo("Failed to fetch required data. Aborting.")
        return

    tools = tools or []

    # Type assertions after null checks
    knowledge = cast(List[Dict[str, Any]], knowledge)
    tools = cast(List[Dict[str, Any]], tools)
    agent_settings = cast(List[Dict[str, Any]], agent_settings)

    # Create knowledge directory and save pages
    knowledge_dir = os.path.join(agent_dir, "knowledge")
    os.makedirs(knowledge_dir, exist_ok=True)

    # Sort knowledge pages by position
    sorted_knowledge = sorted(knowledge, key=lambda x: x.get("position", 0))

    # Show progress while saving knowledge pages
    with click.progressbar(sorted_knowledge, label="Saving knowledge pages") as bar:
        for page in bar:
            filename = f"{page['title']}.md"
            filepath = os.path.join(knowledge_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(page["content"])

    # Create tools directory and save tools
    tools_dir = os.path.join(agent_dir, "tools")
    os.makedirs(tools_dir, exist_ok=True)

    # Show progress while saving tools
    with click.progressbar(tools, label="Saving tools") as bar:
        for tool in bar:
            filename = f"{tool['name']}.yaml"
            filepath = os.path.join(tools_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(tool, f, allow_unicode=True, sort_keys=False)

    # Save agent settings
    with click.progressbar(length=1, label="Saving agent settings") as bar:
        settings_file = os.path.join(agent_dir, "agent-settings.yaml")
        with open(settings_file, "w", encoding="utf-8") as f:
            yaml.dump(agent_settings[0], f, allow_unicode=True, sort_keys=False)
        bar.update(1)

    click.echo(f"Successfully pulled data for agent '{agent}'")


if __name__ == "__main__":
    main()

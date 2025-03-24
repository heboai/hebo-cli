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
@click.option(
    "--dry-run", is_flag=True, help="Validate and preview changes without applying them"
)
@click.argument("agent")
def push(profile, dry_run, agent):
    """Upload local agent content to the Hebo platform."""
    token = get_token(profile)
    deployment_url = get_deployment_url(profile)

    if not token or not deployment_url:
        click.echo(f"Profile '{profile}' not found. Please hebo config it first.")
        return

    headers = {"X-API-Key": token}

    # Validate agent directory exists
    agent_dir = os.path.join(os.getcwd(), agent)
    if not os.path.exists(agent_dir):
        click.echo(
            f"Directory '{agent}' not found. Please run 'hebo pull {agent}' first."
        )
        return

    # Helper function for making POST requests
    def _make_post_request(url, data) -> Optional[Dict[str, Any]]:
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                click.echo(f"Failed to post to {url}: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            click.echo(f"Error connecting to deployment URL: {str(e)}")
            return None

    # Read and prepare knowledge pages
    knowledge_dir = os.path.join(agent_dir, "knowledge")
    knowledge_pages = []
    if os.path.exists(knowledge_dir):
        files = sorted(os.listdir(knowledge_dir))
        for position, filename in enumerate(files):
            if filename.endswith(".md"):
                filepath = os.path.join(knowledge_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                title = filename[:-3]  # Remove .md extension
                knowledge_pages.append(
                    {"title": title, "content": content, "position": position + 1}
                )

    # Read and prepare MCP config
    mcp_config_dir = os.path.join(agent_dir, "mcp-config")
    mcp_configs = []
    if os.path.exists(mcp_config_dir):
        for filename in os.listdir(mcp_config_dir):
            if filename.endswith(".yaml"):
                filepath = os.path.join(mcp_config_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    mcp_config = yaml.safe_load(f)
                    mcp_configs.append(mcp_config)

    # Read agent settings
    settings_file = os.path.join(agent_dir, "agent-settings.yaml")
    if not os.path.exists(settings_file):
        click.echo("Agent settings file not found. Cannot proceed without settings.")
        return

    with open(settings_file, "r", encoding="utf-8") as f:
        agent_settings = yaml.safe_load(f)

    if dry_run:
        click.echo("\nDry run summary:")
        click.echo(f"Knowledge pages to update: {len(knowledge_pages)}")
        for page in knowledge_pages:
            click.echo(f"  - {page['title']}")
        click.echo(f"MCP config to update: {len(mcp_configs)}")
        for config in mcp_configs:
            click.echo(f"  - {config['sse_url']}")
        click.echo("\nAgent settings will be updated")
        return

    # Confirm before proceeding
    if not click.confirm(
        "\nThis will replace all remote content. Do you want to continue?"
    ):
        click.echo("Operation cancelled.")
        return

    # Upload knowledge pages
    click.echo("\nUploading knowledge pages...")
    knowledge_response = _make_post_request(
        f"{deployment_url}/api/knowledge/bulk_update/?agent_version={agent}",
        knowledge_pages,
    )
    if knowledge_response:
        report = knowledge_response.get("report", {})
        click.echo(f"Created: {len(report.get('created', []))} pages")
        click.echo(f"Updated: {len(report.get('updated', []))} pages")
        click.echo(f"Deleted: {len(report.get('deleted', []))} pages")
        if report.get("errors"):
            click.echo("Errors:")
            for error in report["errors"]:
                click.echo(f"  - {error['message']}")

    # Upload agent settings
    click.echo("\nUploading agent settings...")
    settings_response = _make_post_request(
        f"{deployment_url}/api/agent-settings/bulk_update/?agent_version={agent}",
        [agent_settings],
    )
    if settings_response:
        report = settings_response.get("report", {})
        if report.get("errors"):
            click.echo("Errors:")
            for error in report["errors"]:
                click.echo(f"  - {error['message']}")
        else:
            click.echo("Settings updated successfully")

    # Upload MCP config if present
    if mcp_configs:
        click.echo("\nUploading MCP config...")
        mcp_config_response = _make_post_request(
            f"{deployment_url}/api/mcp-config/bulk_update/?agent_version={agent}",
            mcp_configs,
        )
        if mcp_config_response:
            report = mcp_config_response.get("report", {})
            click.echo(f"Created: {len(report.get('created', []))} MCP configs")
            deleted = report.get("deleted", [])
            deleted_count = deleted[0].get("count", 0) if deleted else 0
            click.echo(f"Deleted: {deleted_count} MCP configs")
            if report.get("errors"):
                click.echo("Errors:")
                for error in report["errors"]:
                    click.echo(f"  - {error['message']}")

    click.echo(f"\nSuccessfully pushed data for agent '{agent}'")


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
        mcp_config = _make_request(
            f"{deployment_url}/api/mcp-config/?agent_version={agent}"
        )
        bar.update(1)
        agent_settings = _make_request(
            f"{deployment_url}/api/agent-settings/?agent_version={agent}"
        )
        bar.update(1)

    if knowledge is None or agent_settings is None:
        click.echo("Failed to fetch required data. Aborting.")
        return

    mcp_config = mcp_config or []

    # Type assertions after null checks
    knowledge = cast(List[Dict[str, Any]], knowledge)
    mcp_config = cast(List[Dict[str, Any]], mcp_config)
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

    # Create MCP config directory and save MCP config
    mcp_config_dir = os.path.join(agent_dir, "mcp-config")
    os.makedirs(mcp_config_dir, exist_ok=True)

    # Show progress while saving MCP config
    with click.progressbar(mcp_config, label="Saving MCP config") as bar:
        for i, config in enumerate(bar):
            filename = f"mcp-config-{i}.yaml"
            filepath = os.path.join(mcp_config_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, sort_keys=False)

    # Save agent settings
    with click.progressbar(length=1, label="Saving agent settings") as bar:
        settings_file = os.path.join(agent_dir, "agent-settings.yaml")
        with open(settings_file, "w", encoding="utf-8") as f:
            yaml.dump(agent_settings[0], f, allow_unicode=True, sort_keys=False)
        bar.update(1)

    click.echo(f"Successfully pulled data for agent '{agent}'")


@main.command()
@click.argument("what")
@click.argument("agent")
def add(what, agent):
    """Add new configurations to an agent. Currently supports: mcp-config"""
    if what != "mcp-config":
        click.echo("Currently only 'mcp-config' is supported as the first argument")
        return

    # Validate agent directory exists
    agent_dir = os.path.join(os.getcwd(), agent)
    if not os.path.exists(agent_dir):
        click.echo(
            f"Directory '{agent}' not found. Please run 'hebo pull {agent}' first."
        )
        return

    # Get required sse_url and optional sse_token
    sse_url = click.prompt("Enter SSE URL (required)", type=str)
    if not sse_url:
        click.echo("SSE URL is required")
        return

    sse_token = click.prompt("Enter SSE token (optional, press enter to skip)", type=str, default="", show_default=False)
    sse_token = sse_token if sse_token else None

    # Create or use existing mcp-config directory
    mcp_config_dir = os.path.join(agent_dir, "mcp-config")
    os.makedirs(mcp_config_dir, exist_ok=True)

    # Determine the next index
    existing_configs = [f for f in os.listdir(mcp_config_dir) if f.endswith('.yaml')]
    next_index = len(existing_configs)

    # Create new config
    new_config = {
        "sse_url": sse_url,
        "sse_token": sse_token
    }

    # Save to file
    filename = f"mcp-config-{next_index}.yaml"
    filepath = os.path.join(mcp_config_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(new_config, f, allow_unicode=True, sort_keys=False)

    click.echo(f"Successfully added new MCP config to agent '{agent}'")


if __name__ == "__main__":
    main()

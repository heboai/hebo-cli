import click
import requests
from .config import save_profile, get_token, get_deployment_url


@click.group()
def main():
    pass


@main.command()
def config():
    """Configure the CLI with a profile, deployment URL, and token."""
    profile_name = click.prompt("Enter profile name", type=str, default="default")
    deployment_url = click.prompt("Enter deployment URL", type=str)

    # Validate deployment URL format
    if not deployment_url.startswith(("http://", "https://")):
        deployment_url = f"https://{deployment_url}"

    token = click.prompt("Enter token", type=str, hide_input=True)

    save_profile(profile_name, deployment_url, token)
    click.echo(f"Profile '{profile_name}' configured successfully")


@main.command()
@click.option("--profile", "-p", required=True, help="Profile name to use")
def get_data(profile):
    """Fetch data from the API using the specified profile."""
    token = get_token(profile)
    deployment_url = get_deployment_url(profile)

    if not token or not deployment_url:
        click.echo(f"Profile '{profile}' not found. Please configure it first.")
        return

    headers = {"Authorization": f"Token {token}"}
    try:
        response = requests.get(f"{deployment_url}/api/data/", headers=headers)
        if response.status_code == 200:
            data = response.json()
            click.echo(data)
        else:
            click.echo("Failed to get data")
    except requests.exceptions.RequestException as e:
        click.echo(f"Error connecting to deployment URL: {str(e)}")


if __name__ == "__main__":
    main()

import click
import requests
from .config import get_token, save_token


@click.group()
def main():
    pass


@main.command()
@click.option("--username")
@click.option("--password")
def login(username, password):
    """Login to obtain and store authentication token."""
    response = requests.post(
        "https://example.com/api-token-auth/",
        data={"username": username, "password": password},
    )
    if response.status_code == 200:
        token = response.json()["token"]
        save_token(token)
        click.echo("Login successful")
    else:
        click.echo("Login failed")


@main.command()
def get_data():
    """Fetch data from the API."""
    token = get_token()
    if not token:
        click.echo("Please login first")
        return
    headers = {"Authorization": f"Token {token}"}
    response = requests.get("https://example.com/api/data/", headers=headers)
    if response.status_code == 200:
        data = response.json()
        click.echo(data)
    else:
        click.echo("Failed to get data")


if __name__ == "__main__":
    main()

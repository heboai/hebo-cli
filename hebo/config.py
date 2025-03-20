import os
import json

CONFIG_DIR = os.path.expanduser("~/.hebo")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def save_profile(profile_name, deployment_url, token):
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Load existing config if it exists
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

    # Update or add the profile
    config[profile_name] = {"url": deployment_url, "token": token}

    # Save the updated config
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_FILE, 0o600)  # Set read/write for owner only


def get_profile(profile_name):
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get(profile_name)
    return None


def get_token(profile_name):
    profile = get_profile(profile_name)
    return profile.get("token") if profile else None


def get_deployment_url(profile_name):
    profile = get_profile(profile_name)
    return profile.get("url") if profile else None

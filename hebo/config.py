import os
import json

CONFIG_DIR = os.path.expanduser("~/.hebo")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def save_token(token):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"token": token}, f)
    os.chmod(CONFIG_FILE, 0o600)  # Set read/write for owner only


def get_token():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get("token")
    return None

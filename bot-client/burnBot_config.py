# burnBot_config.py

import configparser
import sys
import os

CONFIG = configparser.ConfigParser()
CONFIG_FILE_PATH = None


def load_config(default_config_file):
    global CONFIG, CONFIG_FILE_PATH

    config_file = sys.argv[1] if len(sys.argv) > 1 else default_config_file

    if not os.path.exists(config_file):
        return None  # Caller should treat missing INI as "first run"

    CONFIG.read(config_file)
    CONFIG_FILE_PATH = os.path.abspath(config_file)
    return config_file


def get_project_dir():
    """Return the directory of the config file, or the directory of the running executable."""
    if CONFIG_FILE_PATH:
        return os.path.dirname(CONFIG_FILE_PATH)
    exe_path = getattr(sys, "executable", None) or sys.argv[0]
    return os.path.dirname(os.path.abspath(exe_path))


def clear_api_credentials_in_ini():
    """Wipe email/password from [api_credentials] in the on-disk INI after first login."""
    if not CONFIG_FILE_PATH:
        return False
    if not CONFIG.has_section("api_credentials"):
        return False

    changed = False
    for key in ("email", "password"):
        if CONFIG.has_option("api_credentials", key) and CONFIG.get("api_credentials", key, fallback="").strip():
            CONFIG.set("api_credentials", key, "")
            changed = True
    if not changed:
        return False
    try:
        with open(CONFIG_FILE_PATH, "w") as fh:
            CONFIG.write(fh)
        return True
    except OSError:
        return False


def resolve_path(path):
    """Resolve a path relative to the project directory. Absolute paths returned as-is."""
    if not path:
        return path
    if os.path.isabs(path):
        return path
    return os.path.abspath(os.path.join(get_project_dir(), path))

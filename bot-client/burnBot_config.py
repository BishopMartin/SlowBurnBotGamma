# burnBot_config.py

import configparser
import sys
import os

CONFIG = configparser.ConfigParser()
CONFIG_FILE_PATH = None


def is_frozen() -> bool:
    """True when running as a PyInstaller-built EXE."""
    return getattr(sys, "frozen", False)


def _baked_to_configparser(baked_cfg: dict) -> configparser.ConfigParser:
    """
    Populate a ConfigParser from the baked DesktopBuildConfig dict so that
    all existing CONFIG.get(...) call sites work unchanged in frozen mode.
    """
    cp = configparser.ConfigParser()
    system_type = baked_cfg.get("system_type", "windows")
    driver_section = f"driver.uchrome.{system_type}"

    cp["api"] = {
        "api_url": baked_cfg.get("api_url", ""),
    }
    cp["api_credentials"] = {
        "email": "",
        "password": "",
    }
    cp["bot_settings"] = {
        "client_id": str(baked_cfg.get("client_id", 1)),
        "client_name": str(baked_cfg.get("client_name", "")),
        "system_type": system_type,
        "bot_debug": str(baked_cfg.get("bot_debug", False)),
        "system_user_agent": baked_cfg.get("system_user_agent", ""),
        "close_browser_session": str(baked_cfg.get("close_browser_session", False)),
        "close_browser_exit": str(baked_cfg.get("close_browser_exit", False)),
        "bot_idle_delay": str(baked_cfg.get("bot_idle_delay", 5)),
    }
    add_args = baked_cfg.get("add_arguments", [])
    cp[driver_section] = {
        "chrome_path": baked_cfg.get("chrome_path", ""),
        "chrome_version": baked_cfg.get("chrome_version", ""),
        "driverType": "webdriver.Chrome",
        "headless": str(baked_cfg.get("headless", False)),
        "detach": str(baked_cfg.get("detach", False)),
        "chrome_user_data_dir_base": baked_cfg.get("chrome_user_data_dir_base", "PortableChrome"),
        "add_argument": "\n".join(add_args) if add_args else "",
    }
    return cp


def load_baked_config():
    """Load customer configuration from the bundled _desktop_build_config module."""
    try:
        import _desktop_build_config as baked  # noqa: PLC0415
        cfg = dict(baked.CONFIG)
        cfg["client_id"] = baked.CLIENT_ID
        cfg["api_url"] = baked.API_URL
        return cfg, baked
    except ImportError:
        raise RuntimeError(
            "Frozen EXE is missing the baked config module (_desktop_build_config). "
            "This EXE was not built correctly."
        )


def load_config(default_config_file):
    global CONFIG, CONFIG_FILE_PATH

    if is_frozen():
        baked_cfg, _ = load_baked_config()
        baked_cp = _baked_to_configparser(baked_cfg)
        for section in baked_cp.sections():
            if not CONFIG.has_section(section):
                CONFIG.add_section(section)
            for key, value in baked_cp.items(section):
                CONFIG.set(section, key, str(value) if value is not None else "")
        CONFIG_FILE_PATH = None
        return None

    config_file = sys.argv[1] if len(sys.argv) > 1 else default_config_file

    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Config file not found: {config_file}")

    CONFIG.read(config_file)
    CONFIG_FILE_PATH = os.path.abspath(config_file)
    return config_file


def get_project_dir():
    """Return the directory of the config file, exe, or cwd."""
    if CONFIG_FILE_PATH:
        return os.path.dirname(CONFIG_FILE_PATH)
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.getcwd()


def clear_api_credentials_in_ini():
    """Wipe email/password from [api_credentials] in the on-disk INI.

    Called after the first successful login so plaintext creds are not left
    on disk (they are stored in the OS keyring instead).  Returns True if
    the file was modified, False otherwise.
    """
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
    project_dir = get_project_dir()
    return os.path.abspath(os.path.join(project_dir, path))

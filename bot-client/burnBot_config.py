# burnBot_config.py

import configparser
import sys, os

CONFIG = configparser.ConfigParser()
CONFIG_FILE_PATH = None

def load_config(default_config_file):
    #default_config_file = "burnBot_config_old.ini"
    global CONFIG_FILE_PATH
    config_file = sys.argv[1] if len(sys.argv) > 1 else default_config_file

    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Config file not found: {config_file}")

    CONFIG.read(config_file)
    CONFIG_FILE_PATH = os.path.abspath(config_file)
    return config_file

def get_project_dir():
    """
    Get the project directory (where the config file is located).
    
    Returns:
        str: Absolute path to the project directory
    """
    if CONFIG_FILE_PATH:
        return os.path.dirname(CONFIG_FILE_PATH)
    # Fallback: use current working directory
    return os.getcwd()

def resolve_path(path):
    """
    Resolve a path relative to the project directory.
    If path is already absolute, return it as-is.
    
    Args:
        path: Path string (can be relative or absolute)
        
    Returns:
        str: Absolute path
    """
    if not path:
        return path
    
    # If path is already absolute, return as-is
    if os.path.isabs(path):
        return path
    
    # Otherwise, resolve relative to project directory
    project_dir = get_project_dir()
    return os.path.abspath(os.path.join(project_dir, path))



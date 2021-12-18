import os
import yaml
from exceptions import ConfigError

def get_config_path():
    if os.environ.get("CONFIG_PATH") is not None:
        return os.environ.get("CONFIG_PATH")
    else:
        raise ConfigError("Could not locate path to config file. Try setting CONFIG_PATH in your environment.")

def load_config():
    config_path = get_config_path()
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigError(f"Could not locate config file '${config_path}'.")
    except yaml.YAMLError:
        raise ConfigError(f"Could not parse YAML config file '${config_path}.")

def save_config(conf):
    config_path = get_config_path()
    with open(config_path, "w") as f:
        yaml.dump(conf, f, default_flow_style=False)


def get_credentials_path():
    credentials_path = os.environ.get("LEAKTHIS_CREDENTIALS_FILE", "")
    if credentials_path == "":
        raise MissingEnvironmentError("LEAKTHIS_CREDENTIALS_FILE")
    return credentials_path

def load_credentials():
    credentials_path = get_credentials_path()
    with open(credentials_path, "r") as f:
        credentials = yaml.safe_load(f)
    return credentials
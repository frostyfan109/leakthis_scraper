import os
import yaml
import portalocker
from commons import get_env_var
from exceptions import ConfigError, MissingEnvironmentError

def get_config_path():
    try:
        return get_env_var("CONFIG_PATH")
    except MissingEnvironmentError:
        raise ConfigError("Could not locate path to config file. Try setting CONFIG_PATH in your environment.")

def load_config():
    config_path = get_config_path()
    try:
        with portalocker.Lock(config_path, "r") as fh:
            return yaml.safe_load(fh)
    except FileNotFoundError:
        raise ConfigError(f"Could not locate config file '${config_path}'.")
    except yaml.YAMLError:
        raise ConfigError(f"Could not parse YAML config file '${config_path}.")

def save_config(conf):
    config_path = get_config_path()
    with portalocker.Lock(config_path, "w") as fh:
        yaml.dump(conf, fh, default_flow_style=False)


def get_credentials_path():
    return get_env_var("LEAKTHIS_CREDENTIALS_FILE")

def load_credentials():
    credentials_path = get_credentials_path()
    with open(credentials_path, "r") as f:
        credentials = yaml.safe_load(f)
    return credentials
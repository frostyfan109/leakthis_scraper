class FileNotFoundError(Exception):
    def __init__(self, url):
        super().__init__(f"File not found at '{url}'.")
        self.url = url

class AuthenticationError(Exception):
    def __init__(self, service, credentials_path):
        super().__init__(f'Failed to authenticate with service "{service}". Credentials path: "{credentials_path}"')
        self.service = service
        self.credentials_path = credentials_path

class MissingEnvironmentError(Exception):
    def __init__(self, env_key):
        super().__init__(f'Required environment variable "{env_key}" is not defined.')

class ConfigError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
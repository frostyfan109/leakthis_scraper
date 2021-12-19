class FileNotFoundError(Exception):
    def __init__(self, url):
        super().__init__(f"File not found at '{url}'.")
        self.url = url

class AuthenticationError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        # super().__init__(f'Failed to authenticate with service "{service}".')

class UnknownHostingServiceError(Exception):
    def __init__(self, url):
        super().__init__(f"Could not identify associated service for url '{url}'.")
        self.url = url

class MissingEnvironmentError(Exception):
    def __init__(self, env_key):
        super().__init__(f'Required environment variable "{env_key}" is not defined.')
        self.env_key = env_key

class ConfigError(Exception):
    def __init__(self, msg):
        super().__init__(msg)

class StorageError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
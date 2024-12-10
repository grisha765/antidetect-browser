import os
from dotenv import load_dotenv

class Config:
    log_level: str = "INFO"
    proxy_host: str = '127.0.0.1'
    proxy_port: int = 8080
    proxy_user: str = 'user'
    proxy_pass: str = 'passwd'
    url: str = 'https://browserleaks.com'
    chromedriver_path: str = '/usr/bin/chromedriver'
    cookies_path: str = './cookies/'

    @classmethod
    def load_from_env(cls):
        load_dotenv()
        for key in cls.__annotations__:
            env_value = os.getenv(key.upper())
            if env_value is not None:
                current_value = getattr(cls, key)
                if isinstance(current_value, int):
                    setattr(cls, key, int(env_value))
                elif isinstance(current_value, list):
                    setattr(cls, key, env_value.split(","))
                else:
                    setattr(cls, key, env_value)

Config.load_from_env()

if __name__ == "__main__":
    raise RuntimeError("This module should be run only via main.py")

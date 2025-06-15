from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):

    bot_token: SecretStr
    admin: SecretStr

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


config = Settings()


class UserParams():
    def __init__(self):
        self.only_maturity = True
        self.res_count = 5
        pass

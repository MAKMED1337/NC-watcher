from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(BaseSettings):
    model_config = SettingsConfigDict(env_file='env/reporter.env')

    group_id: int


env = Env()

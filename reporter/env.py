from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(BaseSettings):
    model_config = SettingsConfigDict(env_file='env/reporter.env')

    TOKEN: str  # FIXME: it's not neccesary field, but won't work without it
    BOT_NAME: str  # FIXME: it's not neccesary field, but won't work without it
    group_id: int


env = Env()

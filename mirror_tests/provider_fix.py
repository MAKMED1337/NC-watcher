import helper.provider_config as config
from near.providers import JsonProvider

config.provider = JsonProvider('localhost:3030')
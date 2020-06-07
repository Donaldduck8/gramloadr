import os
from helpers import *
import json

config = {}

def validate_config(config):
    ok = True
    ok &= exists(config, ['COLOR'])
    ok &= exists(config, ['COLOR', 'HIGHLIGHTS'])
    ok &= exists(config, ['COLOR', 'IGTV'])
    ok &= exists(config, ['COLOR', 'LIVESTREAMS'])
    ok &= exists(config, ['COLOR', 'PAGES'])
    ok &= exists(config, ['COLOR', 'STORIES'])

    ok &= exists(config, ['COOLDOWN'])
    ok &= exists(config, ['COOLDOWN', 'HIGHLIGHTS_IGTV'])
    ok &= exists(config, ['COOLDOWN', 'LIVESTREAMS'])
    ok &= exists(config, ['COOLDOWN', 'PAGES'])
    ok &= exists(config, ['COOLDOWN', 'STORIES'])

    ok &= exists(config, ['USERNAMES_TO_GRAB'])
    ok &= exists(config, ['USERNAMES_TO_GRAB', 'HIGHLIGHTS_IGTV'])
    ok &= exists(config, ['USERNAMES_TO_GRAB', 'LIVESTREAMS'])
    ok &= exists(config, ['USERNAMES_TO_GRAB', 'PAGES'])
    ok &= exists(config, ['USERNAMES_TO_GRAB', 'STORIES'])

    ok &= exists(config, ['USER_DIRECTORY'])
    return ok


def create_config(config_path):
    default = \
    {
        'COLOR' : {
            'HIGHLIGHTS' : '#003A50',
            'IGTV' : '#FCB9B0',
            'LIVESTREAMS' : '#FF0000',
            'PAGES' : '#FFCDAC',
            'STORIES' : '#ECC699'
        },
        'COOLDOWN' : {
            'HIGHLIGHTS_IGTV' : 6400,
            'LIVESTREAMS' : 120,
            'PAGES' : 7200,
            'STORIES' : 600
        },
        'USERNAMES_TO_GRAB': {
            'HIGHLIGHTS_IGTV' : [],
            'LIVESTREAMS' : [],
            'PAGES' : [],
            'STORIES' : []
        },
        'USER_DIRECTORY' : ''
    }

    with open(config_path, 'wb') as config_file:
        config_file.write(json.dumps(default, sort_keys=True, indent=4).encode())


def load_config(config_path):
    global config

    # Check if configuration file exists
    if not os.path.isfile(config_path):
        print('Could not find configuration file. Creating default configuration...')
        create_config(config_path)
        print(str.format('A default configuration file was created at {}.\nPlease modify this and re-run the script.', config_path))
        return False

    with open(config_path, 'rb') as config_file:
        config_loaded = json.loads(config_file.read())

    if not config_loaded:
        print('Could not read configuration file. Creating default configuration...')
        create_config(config_path)
        print(str.format('A default configuration file was created at {}.\nPlease modify this and re-run the script.', config_path))
        return False

    if not validate_config(config_loaded):
        print('Could not validate configuration file. Aborting...')
        return False

    if len(config_loaded['USER_DIRECTORY']) == 0:
        config_loaded['USER_DIRECTORY'] = os.getcwd()

    config = config_loaded

    return True


def get_config():
    global config
    return config


def config_main():
    return load_config(os.path.join(os.getcwd(), 'config.json'))

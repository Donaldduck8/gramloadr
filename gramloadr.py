import sys
import requests
import argparse
import grab_pages
import grab_stories
import grab_highlights
import grab_livestreams
import multiprocessing
import print_helpers
from config import *
from login import *

processes = []

def init_proc(target, args):
    comp_p = multiprocessing.Process(target=target, args=args)
    processes.append(comp_p)
    comp_p.start()

def wait():
    for proc in processes:
        proc.join()

def launch():
    # Prepare argument structure
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-highlights", action="store_true")
    parser.add_argument("-livestreams", action="store_true")
    parser.add_argument("-igtv", action="store_true")
    parser.add_argument("-pages", action="store_true")
    parser.add_argument("-stories", action="store_true")

    parser.add_argument("--username")
    parser.add_argument("--password")

    # Parse arguments
    args = parser.parse_args()

    # Back up username and password from arguments
    username = None
    password = None

    if args.username and args.password:
        username = args.username
        password = args.password


    # Find sessions.json
    sessions_file_path = os.path.join(os.getcwd(), 'sessions.json')

    # If username and password are provided, log in and update session IDs
    if args.username and args.password:
        (sessionid_desktop, user_agent_desktop, csrftoken_desktop) = login_desktop(args.username, args.password)

        if not sessionid_desktop:
            print('Desktop login failed')
            return

        time.sleep(1)

        (sessionid_mobile, user_agent_mobile, csrftoken_mobile) = login_mobile(args.username, args.password)

        if not sessionid_mobile:
            print('Mobile login failed')
            return

        with open(sessions_file_path, 'w+') as sessions_file:
            sessions_file.write(json.dumps({'desktop':{'sessionid' : sessionid_desktop, 'user_agent' : user_agent_desktop, 'csrftoken' : csrftoken_desktop},
                                              'mobile':{'sessionid' : sessionid_mobile, 'user_agent' : user_agent_mobile, 'csrftoken' : csrftoken_mobile}}, sort_keys=True, indent=4))
    else:
        # If sessions.json exists, try to read it, otherwise quit and tell user to log in
        try:
            # Doesn't exist
            if not os.path.isfile(sessions_file_path):
                raise Exception

            # Read session IDs
            with open(sessions_file_path, 'r+') as sessions_file:
                sessions_dict = json.loads(sessions_file.read())

                sessionid_desktop = sessions_dict['desktop']['sessionid']
                user_agent_desktop = sessions_dict['desktop']['user_agent']
                csrftoken_desktop = sessions_dict['desktop']['csrftoken']

                sessionid_mobile = sessions_dict['mobile']['sessionid']
                user_agent_mobile = sessions_dict['mobile']['user_agent']
                csrftoken_mobile = sessions_dict['mobile']['csrftoken']

        except Exception as e:
            print('Sessions could not be found. Please run gramloadr with --username and --password to log in.')
            return

    # Load and validate configuration
    if not config_main():
        print('Could not load configuration')
        return

    config_obj = get_config()

    # If no user directory is specified, use CWD
    if not config_obj['USER_DIRECTORY']:
        config_obj['USER_DIRECTORY'] = os.getcwd()
    else:
        config_obj['USER_DIRECTORY'] = config_obj['USER_DIRECTORY'].replace('/', '\\')

    # Try to create user directory if necessary, if this fails, return
    if not os.path.isdir(config_obj['USER_DIRECTORY']):
        os.makedirs(config_obj['USER_DIRECTORY'])

        if not os.path.isdir(config_obj['USER_DIRECTORY']):
            print('Could not create user directory')
            return

    # Create authenticated desktop and mobile sessions
    session_desktop = requests.Session()
    session_desktop.cookies.update({'sessionid' : sessionid_desktop, 'csrftoken' : csrftoken_desktop})
    session_desktop.headers.update({'User-Agent' : user_agent_desktop})

    session_mobile = requests.Session()
    session_mobile.cookies.update({'sessionid' : sessionid_mobile, 'csrftoken' : csrftoken_mobile})
    session_mobile.headers.update({'User-Agent' : user_agent_mobile})

    sessions = {'desktop_auth' : session_desktop, 'mobile_auth' : session_mobile}

    all_modules = True

    if args.highlights:
        if args.igtv:
            init_proc(target=grab_highlights.run, args=(sessions,
                                                        config_obj['COOLDOWN']['HIGHLIGHTS_IGTV'],
                                                        config_obj['USERNAMES_TO_GRAB']['HIGHLIGHTS_IGTV'],
                                                        config_obj['USER_DIRECTORY'],
                                                        ['-IGTV']))
        else:
            init_proc(target=grab_highlights.run, args=(sessions,
                                                        config_obj['COOLDOWN']['HIGHLIGHTS_IGTV'],
                                                        config_obj['USERNAMES_TO_GRAB']['HIGHLIGHTS_IGTV'],
                                                        config_obj['USER_DIRECTORY'],
                                                        []))
        all_modules = False
    if args.livestreams:
        init_proc(target=grab_livestreams.run, args=(sessions,
                                                     config_obj['COOLDOWN']['LIVESTREAMS'],
                                                     config_obj['USERNAMES_TO_GRAB']['LIVESTREAMS'],
                                                     config_obj['USER_DIRECTORY']))
        all_modules = False
    if args.pages:
        init_proc(target=grab_pages.run, args=(sessions,
                                               config_obj['COOLDOWN']['PAGES'],
                                               config_obj['USERNAMES_TO_GRAB']['PAGES'],
                                               config_obj['USER_DIRECTORY']))
        all_modules = False
    if args.stories:
        init_proc(target=grab_stories.run, args=(sessions,
                                                 config_obj['COOLDOWN']['STORIES'],
                                                 config_obj['USERNAMES_TO_GRAB']['STORIES'],
                                                 config_obj['USER_DIRECTORY']))
        all_modules = False

    if all_modules:
        init_proc(target=grab_highlights.run, args=(sessions,
                                                    config_obj['COOLDOWN']['HIGHLIGHTS_IGTV'],
                                                    config_obj['USERNAMES_TO_GRAB']['HIGHLIGHTS_IGTV'],
                                                    config_obj['USER_DIRECTORY'],
                                                    ['-IGTV']))
        init_proc(target=grab_livestreams.run, args=(sessions,
                                                     config_obj['COOLDOWN']['LIVESTREAMS'],
                                                     config_obj['USERNAMES_TO_GRAB']['LIVESTREAMS'],
                                                     config_obj['USER_DIRECTORY']))
        init_proc(target=grab_pages.run, args=(sessions,
                                               config_obj['COOLDOWN']['PAGES'],
                                               config_obj['USERNAMES_TO_GRAB']['PAGES'],
                                               config_obj['USER_DIRECTORY']))
        init_proc(target=grab_stories.run, args=(sessions,
                                                 config_obj['COOLDOWN']['STORIES'],
                                                 config_obj['USERNAMES_TO_GRAB']['STORIES'],
                                                 config_obj['USER_DIRECTORY']))

    wait()

if __name__ == '__main__':
    launch()

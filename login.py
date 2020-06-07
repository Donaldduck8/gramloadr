import requests
import datetime
import urllib.parse
import time
import random
from fake_useragent import UserAgent

def login_desktop(username, passwd):
    try:
        # Create desktop session
        session_desktop = requests.Session()

        # Generate "encrypted" password, mode 0 allows plain-text credentials
        enc_password_desktop = '#PWD_INSTAGRAM_BROWSER:0:{}:{}'.format(int(datetime.datetime.now().timestamp()), passwd)

        # TODO: Generate and return User-Agent
        user_agent_desktop = create_user_agent(desktop=True)

        # Update session headers
        session_desktop.headers.update({'User-Agent': user_agent_desktop, 'Cookie':'ig_cb=1'})

        # Get CSRF-Token
        session_desktop.get('https://www.instagram.com/web/__mid/', allow_redirects=True)

        csrf_token = session_desktop.cookies.get_dict()['csrftoken']
        session_desktop.headers.update({'X-CSRFToken': csrf_token})

        # Log in
        login = session_desktop.post('https://www.instagram.com/accounts/login/ajax/', data={'enc_password': enc_password_desktop, 'username': username}, allow_redirects=True)

        # Catch challenges
        if 'challenge' in login.text:
            print('A challenge was encountered while logging in. You must resolve this challenge by logging in normally through a web browser.')
            print(login.text)
            return None

        # Return plain-text session ID
        enc_sessionid = login.cookies.get_dict()['sessionid']
        return (urllib.parse.unquote(enc_sessionid), user_agent_desktop, csrf_token)

    except Exception as e:
        print(e)
        return None


def login_mobile(username, passwd):
    try:
        # Create mobile session
        session_mobile = requests.Session()
        session_mobile.headers.update({})
        mobile_login_url = 'https://i.instagram.com/api/v1/accounts/login/'

        # Generate "encrypted" password, mode 0 allows plain-text credentials
        enc_password_mobile = '#PWD_INSTAGRAM:0:{}:{}'.format(int(datetime.datetime.now().timestamp()), passwd)

        # Generate random device ID
        random_hex_string = random.choices('0123456789abcdef', k=16)
        random_device_id = 'android-' + ''.join(map(str, random_hex_string))

        # Assemble data for login POST request body
        dict = {'enc_password' : enc_password_mobile, 'username' : username, 'device_id' : random_device_id}
        dict_string = str(dict).replace(' ', '').replace('\'', '\"')

        enc_body = 'signed_body=SIGNATURE.' + urllib.parse.quote(dict_string)

        # TODO Generate and return User-Agent
        user_agent_mobile = create_user_agent(desktop=False)

        # Update session headers
        session_mobile.headers.update({'User-Agent': user_agent_mobile, 'Cookie':'ig_cb=1'})

        # Get CSRF-Token
        r = session_mobile.get('https://b.i.instagram.com/api/v1/zr/token/result/')
        csrf_token = session_mobile.cookies.get_dict()['csrftoken']

        # Set headers for login request
        session_mobile.headers.update({'Content-Type' : 'application/x-www-form-urlencoded; charset=UTF-8', 'X-CSRFToken': csrf_token})

        # Send login request
        login = session_mobile.post(mobile_login_url, data=enc_body)

        # Catch challenges
        if 'challenge' in login.text:
            print('A challenge was encountered while logging in. You must resolve this challenge by logging in normally through the app.')
            print(login.text)
            return None

        # Return plain-text session ID
        enc_sessionid = login.cookies.get_dict()['sessionid']
        return (urllib.parse.unquote(enc_sessionid), user_agent_mobile, csrf_token)
    except Exception as e:
        print(e)
        return None

def create_user_agent(desktop):
    INSTAGRAM_AGENT_VERSION = 'Instagram 144.0.0.25.119 Android'
    INSTAGRAM_VERSION_ID = 217948947

    ANDROID_VERSION = '26/8.0.0'

    if desktop:
        ua = UserAgent()
        user_agents = [ua.opera, ua.chrome, ua.google, ua.firefox, ua.ff, ua.safari]

        index = random.randint(0, len(user_agents) - 1)
        return user_agents[index]
    else:
        dpi = '600dpi'
        res = '1440x3040'

        model_names = ['samsung; SM-G960F', 'samsung; SM-G960W', 'samsung; SM-A707F',
                       'samsung; SM-G950F', 'samsung; SM-G9508', 'samsung; SM-A405F',
                       'motorola; motorola one', 'LENOVO/Lenovo; Lenovo K33b36',
                       'motorola; Moto G (5)', 'asus; ASUS_X00LD', 'HUAWEI; WAS_LX1A'
                       'LGE/lge; LG-LS777', 'Sony; G8341', 'LGE/lge; LG-M250']

        index = random.randint(0, len(model_names) - 1)
        model_info = model_names[index]
        lang = 'en_US'

        ua = INSTAGRAM_AGENT_VERSION + ' (' + str('; '.join([ANDROID_VERSION, dpi, res, model_info, lang, str(INSTAGRAM_VERSION_ID)])) + ')'
        return ua

import os
import re
import json
import time
import datetime
import requests
from colored import fg, attr
from helpers import *
from print_helpers import formatted_print
from mutagen.mp4 import MP4, MP4Cover

user_following_ids = []
usernames_to_grab = []
text_format = (fg(77), attr(0))

# Find and download Instagram TV from highlight reel data
def grab_igtv(session, highlight_reel_data, user_dir):
    # Check if the user has any IGTV videos
    if exists(highlight_reel_data, ['tv_channel']):
        for item in highlight_reel_data['tv_channel']['items']:
            # Grab necessary data
            username = item['user']['username']
            timestamp = re.sub('[: ]', '-', str(datetime.datetime.fromtimestamp(item['taken_at'])))
            id = item['id'].rsplit('_')[0]
            video_url = item['video_versions'][0]['url']

            # Check if there is a description
            if exists(item, ['caption','text']):
                description = item['caption']['text']

            # Set up directories for saving
            igtv_directory = os.path.join(user_dir, str(username), 'IGTV')
            if not os.path.isdir(igtv_directory):
                os.makedirs(igtv_directory)

            save_path = os.path.join(igtv_directory, str(timestamp) + '.mp4')

            # Don't redownload existing IGTV
            if not os.path.isfile(save_path):
                formatted_print('IGTV', str.format("Downloaded IGTV by {} uploaded at {}", username, timestamp))
                video_data = retry_network_wrapper(session.get, [video_url]).content
                with open(save_path, 'wb') as video_file:
                    video_file.write(video_data)

                # Tag video with description if it exists
                if description:
                    vid = MP4(save_path)
                    vid['\xa9cmt'] = description
                    vid.save(save_path)

            time.sleep(0.5)

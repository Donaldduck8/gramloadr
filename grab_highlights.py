import os
import re
import sys
import json
import time
import natsort
import datetime
import requests
from helpers import *
from mutagen.mp4 import MP4
from story_helpers import *
from print_helpers import formatted_print
from colored import fg, attr
from natsort import natsorted
from grab_igtv import grab_igtv


# Find and download video and image highlights from specified users (all users if none specified)
def grab_highlights(sessions, id_list, user_dir, args):
    session_desktop = sessions['desktop_auth']
    session_mobile = sessions['mobile_auth']

    formatted_print('HIGHLIGHTS', 'Checking for highlights...')

    # Collect IDs of highlight reels
    highlight_reels = []

    for id in id_list:
        highlight_reel_url = str.format('https://i.instagram.com/api/v1/highlights/{}/highlights_tray/', id)
        highlight_reel_data = json.loads(retry_network_wrapper(session_mobile.get, [highlight_reel_url]).text)

        if '-IGTV' in args:
            grab_igtv(session_mobile, highlight_reel_data, user_dir)

        for tray in highlight_reel_data['tray']:
            highlight_reels.append((tray['id'], tray['user']['username'], sanitize_string(tray['title'])))

        time.sleep(10)

    # It's possible to provide multiple highlight reel IDs in one request,
    # but requesting too many at once tends to produce server errors.
    # Partitioning the set of IDs into smaller chunks seems like a good solution.

    partition_size = 15
    partitioned_highlight_reels = partition_list(highlight_reels, partition_size)
    partition_count = len(partitioned_highlight_reels)

    for i, provided_highlight_reels in enumerate(partitioned_highlight_reels):
        formatted_print('HIGHLIGHTS', str.format('Checking partition {} of {}', i + 1, partition_count))

        # Concatenate all provided IDs into a string
        highlight_reel_ids = []
        for id, username, title in provided_highlight_reels:
            highlight_reel_ids.append(id)

        # Get all highlight reels in the partition at once
        highlight_reels_url = 'https://i.instagram.com/api/v1/feed/reels_media/'
        reel_ids_dict = {'user_ids'}
        body = 'signed_body=SIGNATURE.{"user_ids":' + str(highlight_reel_ids).replace('\'', '\"').replace(' ', '') + '}'

        #TODO: cookie jar or something, terrible hack.
        session_mobile.headers.update({'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})

        highlight_reels_data = json.loads(session_mobile.post(highlight_reels_url, body).text)
        #highlight_reels_data = json.loads(retry_network_wrapper(session_mobile.post, [highlight_reels_url, body.encode()], sleep_amount=30).text)

        for id, username, title in provided_highlight_reels:
            # Get highlight reel
            highlight_reel = highlight_reels_data['reels'][id]

            # Navigate to highlight folder
            highlight_directory = os.path.join(user_dir, str(username), 'Highlights', title + '_' + id.split(':')[1])

            # Create highlight folder if it doesn't exist yet
            if not os.path.isdir(highlight_directory):
                os.makedirs(highlight_directory)

            for item in highlight_reel['items']:
                # Initialization
                timestamp = re.sub('[: ]', '-', str(datetime.datetime.fromtimestamp(item['taken_at'])))
                highlight_is_video = True if item['media_type'] == 2 else False
                highlight_url = ''

                # Check if story is a video or an image
                if highlight_is_video:
                    highlight_url = item['video_versions'][0]['url']
                    save_path = os.path.join(highlight_directory, str(timestamp) + '.mp4')
                else:
                    highlight_url = item['image_versions2']['candidates'][0]['url']
                    save_path = os.path.join(highlight_directory, str(timestamp) + '.jpg')

                # Don't redownload existing files
                if not os.path.isfile(save_path):
                    # Save embedded URLs
                    comment = ''
                    comment = get_swipe(item, comment)
                    comment = get_attribution_url(item, comment)
                    comment = get_tappable_object(item, comment)

                    get_story_music_stickers(item, save_path, session_mobile)

                    highlight_file_data = retry_wrapper(session_mobile.get, [highlight_url], 10, 1)

                    with open(save_path, 'wb') as highlight_file:
                        highlight_file.write(highlight_file_data.content)
                        formatted_print('HIGHLIGHTS', str.format("Downloaded {} highlight by {} uploaded at {}", "video" if highlight_is_video else "image", username, timestamp))

                    # Embed metadata if there is any
                    if len(comment) > 0:
                        if highlight_is_video:
                            vid = MP4(save_path)
                            vid['\xa9cmt'] = comment
                            vid.save(save_path)
                        else:
                            set_comment(save_path, comment)

                time.sleep(0.2)
            time.sleep(5)





# Runs
def run(sessions, cooldown, usernames_to_grab, user_dir, args):
    own_user_id = sessions['desktop_auth'].cookies['sessionid'].split(':')[0]

    while True:
        grab_highlights(sessions, grab_following_ids(own_user_id, usernames_to_grab, sessions['desktop_auth']), user_dir, args)
        formatted_print('HIGHLIGHTS', 'Check complete!')
        formatted_print('HIGHLIGHTS', 'Sleeping...')
        time.sleep(cooldown)

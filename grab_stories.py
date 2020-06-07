import os
import re
import json
import time
import datetime
import requests
from colored import fg, attr
from helpers import *
from mutagen.mp4 import MP4, MP4Cover
from story_helpers import *
from print_helpers import formatted_print

user_following_ids = []
usernames_to_grab = []


# Find and download video and image stories from specified users (all users if none specified)
def grab_stories(sessions, id_list, user_dir):
    session_desktop = sessions['desktop_auth']
    session_mobile = sessions['mobile_auth']

    formatted_print('STORIES', 'Checking for stories...')

    stories_url = construct_queryhash_url('0a85e6ea60a4c99edc58ab2f3d17cfdf', reel_ids=id_list, precomposed_overlay='false')
    stories = retry_network_wrapper(session_desktop.get, [stories_url], sleep_amount=30)

    story_info = json.loads(stories.text)

    for i, __user in enumerate(story_info['data']['reels_media']):
        for __j, item in enumerate(story_info['data']['reels_media'][i]['items']):
            # Initialization
            username = story_info['data']['reels_media'][i]['user']['username']
            user_id = item['owner']['id']
            timestamp = re.sub('[: ]', '-', str(datetime.datetime.fromtimestamp(item['taken_at_timestamp'])))
            story_is_video = str(item['is_video']) == 'True'
            story_url = ''
            story_id = item['id']

            # Navigate to stories folder
            story_directory = os.path.join(user_dir, str(username), 'Stories')

            # Check if story is a video or an image
            if story_is_video:
                story_url = item['video_resources'][len(item['video_resources']) - 1]['src']
                save_path = os.path.join(story_directory, str(timestamp) + '.mp4')
            else:
                story_url = item['display_resources'][len(item['display_resources']) - 1]['src']
                save_path = os.path.join(story_directory, str(timestamp) + '.jpg')

            # Save embedded URLs
            comment = ''
            comment = get_swipe(item, comment)
            comment = get_attribution_url(item, comment)
            comment = get_tappable_object(item, comment)


            # Create stories folder if it doesn't exist yet
            if not os.path.isdir(story_directory):
                os.makedirs(story_directory)

            # Don't redownload existing files
            if not os.path.isfile(save_path):
                # Grab embedded audio using mobile-only query
                if session_mobile and exists(item, ['muting_info']):
                    mobile_story_url = str.format('https://i.instagram.com/api/v1/feed/user/{}/story/', user_id)
                    mobile_story_data = retry_network_wrapper(session_mobile.get, [mobile_story_url]).text
                    mobile_stories = json.loads(mobile_story_data)
                    mobile_story = None

                    for __i, mobile_item in enumerate(mobile_stories['reel']['items']):
                        mobile_id = str(mobile_item['id']).split('_')[0]

                        if story_id == mobile_id:
                            mobile_story = mobile_item

                        if mobile_story:
                            get_story_music_stickers(mobile_story, save_path, session_desktop)

                story_file_data = retry_network_wrapper(session_desktop.get, [story_url])
                display_text = str.format('Downloaded {} story by {} uploaded at {}',
                                          'video' if story_is_video else 'image', username, timestamp)
                formatted_print('STORIES', display_text)
                with open(save_path, 'wb') as story_file:
                    story_file.write(story_file_data.content)

                # Embed metadata if there is any
                if len(comment) > 0:
                    if story_is_video:
                        vid = MP4(save_path)
                        vid['\xa9cmt'] = comment
                        vid.save(save_path)
                    else:
                        set_comment(save_path, comment)

def run(sessions, cooldown, usernames, user_dir):
    usernames_to_grab = usernames

    own_user_id = sessions['desktop_auth'].cookies['sessionid'].split(':')[0]

    while True:
        grab_stories(sessions, grab_following_ids(own_user_id, usernames_to_grab, sessions['desktop_auth']), user_dir)
        formatted_print('STORIES', 'Check Completed!')
        formatted_print('STORIES', 'Sleeping...')
        time.sleep(cooldown)

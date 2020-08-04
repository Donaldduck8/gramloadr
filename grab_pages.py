import os
import re
import json
import time
import datetime
import requests
from helpers import *
from colored import fg, attr
from print_helpers import formatted_print
from mutagen.mp4 import MP4

user_following_ids = []
usernames_to_grab = []


# Find and download video and image pages from specified users (all users if none specified)
def grab_pages(sessions, username_list, user_dir):
    for id, username in username_list:
        formatted_print('PAGES', str.format('Checking pages from {}...', username))
        session_desktop = sessions['desktop_auth']
        session_mobile = sessions['mobile_auth']

        user_page_mobile_json = json.loads(retry_network_wrapper(session_mobile.get, [str.format('https://i.instagram.com/api/v1/users/{}/info/', id)]).text)
        user = user_page_mobile_json['user']
        has_igtv_videos = user['total_igtv_videos'] > 0

        time.sleep(10)

        # Define and create directories
        user_directory = os.path.join(user_dir, username, 'Page')
        user_posts_directory = os.path.join(user_dir, username, 'Posts')

        if not os.path.isdir(user_directory):
            os.makedirs(user_directory)
        if not os.path.isdir(user_posts_directory):
            os.makedirs(user_posts_directory)

        # Update page_info.json if it exists, create and save it if it doesn't exist
        page_info_json_path = os.path.join(user_directory, "page_info.json")
        if os.path.isfile(page_info_json_path):
            user_info_dict = json.loads(open(page_info_json_path, "r+", encoding='utf8').read())
        else:
            user_info_dict = {}

        #TODO: REFACTOR
        def update_dict(user_info_dict, field_name, timestamp, content):
            if content is None:
                return

            new_obj = {'timestamp' : timestamp, 'content' : content}

            if field_name not in user_info_dict:
                user_info_dict[field_name] = [new_obj]
                return

            if len(user_info_dict[field_name]) == 0:
                user_info_dict[field_name].append(new_obj)
                return

            content_recent = user_info_dict[field_name][len(user_info_dict[field_name]) - 1]['content']
            if content != content_recent:
                user_info_dict[field_name].append(new_obj)
                return

        # Get biography and full name
        timestamp = int(datetime.datetime.now().timestamp())
        biography = user['biography']
        full_name = user['full_name']

        update_dict(user_info_dict, 'full_name', timestamp, full_name)
        update_dict(user_info_dict, 'biography', timestamp, biography)

        if exists(user, ['public_email']):
            update_dict(user_info_dict, 'email', timestamp, user['public_email'])

        if exists(user, ['public_phone_number']):
            update_dict(user_info_dict, 'phone_number', timestamp, user['public_phone_number'])

        if exists(user, ['external_url']):
            update_dict(user_info_dict, 'external_url', timestamp, user['external_url'])

        # Write dictionary
        with open(page_info_json_path, 'w+', encoding='utf8') as user_dict_file:
            user_dict_file.write(json.dumps(user_info_dict, sort_keys=True, indent=4, ensure_ascii=False))

        # Download profile picture
        profile_pic_url_hd = user['hd_profile_pic_url_info']['url']
        profile_pic_filename = 'avatar_' + re.sub(r'^.*/(.*?)\?.*$', r'\1', profile_pic_url_hd)
        profile_pic_path = os.path.join(user_directory, profile_pic_filename)
        if not os.path.isfile(profile_pic_path):
            profile_pic_data = retry_network_wrapper(session_desktop.get, [profile_pic_url_hd], 5, 1, [200])
            open(profile_pic_path, "wb").write(profile_pic_data.content)

            formatted_print('PAGES', str.format('Downloaded avatar from {}...', username))

            # Write biography to the comments field of the profile picture
            set_comment(profile_pic_path, biography)

        has_next_page = True
        end_cursor = ''

        # Iterate through pages, 50 posts at a time
        while has_next_page:
            user_page_url = construct_queryhash_url('44efc15d3c13342d02df0b5a9fa3d33f', id=id, first=50, after=end_cursor)
            user_page_json = json.loads(retry_network_wrapper(session_desktop.get, [user_page_url], retry_count_limit=5, sleep_amount=2).text)
            user = user_page_json['data']['user']

            has_next_page = user['edge_owner_to_timeline_media']['page_info']['has_next_page']
            end_cursor = user['edge_owner_to_timeline_media']['page_info']['end_cursor']
            if end_cursor is None:
                end_cursor = ''

            # Iterate over all edges (posts)
            for i, edge in enumerate(user['edge_owner_to_timeline_media']['edges']):
                comment = ''

                if edge['node']['location'] is not None:
                    comment += '[Location]\n' + edge['node']['location']['name'] + '\n\n'

                if len(edge['node']['edge_media_to_caption']['edges']) > 0:
                    comment += '[Caption]\n' + edge['node']['edge_media_to_caption']['edges'][0]['node']['text'] + '\n\n'

                timestamp = edge['node']['taken_at_timestamp']
                typename = edge['node']['__typename']
                formatted_timestamp = str(datetime.datetime.fromtimestamp(timestamp))
                is_video = edge['node']['is_video']

                edge_src = edge_filename = ''
                edges = []

                if typename == 'GraphSidecar':
                    # Iterate over edges, add each to internal list
                    for j, child_edge in enumerate(edge['node']['edge_sidecar_to_children']['edges']):
                        edges.append(child_edge)
                else:
                    # Add edge to internal list
                    edges.append(edge)

                for edge in edges:
                    # Get original URL
                    is_video = edge['node']['is_video']
                    if is_video:
                        edge_src = edge['node']['video_url']
                    else:
                        edge_src = edge['node']['display_resources'][len(edge['node']['display_resources']) - 1]['src']

                    # Extract parameters from URL
                    image_id = re.sub(r'^.*/(.*?)\?.*$', r'\1', edge_src)
                    extension = image_id.split('.')[-1]

                    # Filename = timestamp + _ + first bit of image ID
                    edge_filename = re.sub('[: ]', '-', formatted_timestamp) + '_' + image_id.split('_')[0] + '.' + extension
                    edge_path = os.path.join(user_posts_directory, edge_filename)

                    # Don't redownload
                    if not os.path.isfile(edge_path):
                        formatted_print('PAGES', str.format('Downloading {} from {} uploaded at {}...', 'video' if is_video else 'image', username, formatted_timestamp))
                        edge_data = retry_network_wrapper(session_desktop.get, [edge_src], 5, 1, [200])
                        open(edge_path, "wb").write(edge_data.content)

                        # Save caption information into comments field for downloaded media
                        if len(comment) > 0:
                            if is_video:
                                vid = MP4(edge_path)
                                vid['\xa9cmt'] = comment
                                vid.save(edge_path)
                            else: # Please never be a PNG, thanks.
                                set_comment(edge_path, comment)

            time.sleep(12)
        time.sleep(12)


def run(sessions, cooldown, usernames, user_dir):
    usernames_to_grab = usernames

    own_user_id = sessions['desktop_auth'].cookies['sessionid'].split(':')[0]

    while True:
        grab_pages(sessions, grab_following_ids_and_names(own_user_id, usernames_to_grab, sessions['desktop_auth']), user_dir)
        formatted_print('PAGES', 'Check complete!')
        formatted_print('PAGES', 'Sleeping...')

        time.sleep(cooldown)

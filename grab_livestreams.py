import os
import json
import time
import ffmpy
import string
import shutil
import config
import datetime
import requests
import threading
import multiprocessing
from helpers import *
from colored import fg, attr
from natsort import natsorted
from print_helpers import formatted_print
from mpegdash.parser import MPEGDASHParser

# Keep track of currently downloading broadcasts
processes = []
current_broadcasts = []

# Grabs the initialization media for the broadcast
def grab_initialization_media(stream_server_directory, stream_id, session):
    init_video_url = stream_server_directory + '/live-hd-v/' + stream_id + '_0-init.m4v'
    init_audio_url = stream_server_directory + '/live-hd-a/' + stream_id + '_0-init.m4a'

    try:
        initialization_video = retry_network_wrapper(session.get, [init_video_url])
        initialization_audio = retry_network_wrapper(session.get, [init_audio_url])
    except Exception as e:
        formatted_print('LIVESTREAMS', 'Initialization media not yet available')

    return initialization_video, initialization_audio


# Grabs and creates video and audio segments
def grab_media(current_segment, stream_server_directory, stream_time, stream_id, live_username, session, user_dir):
    segment_video_url = stream_server_directory + '/live-hd-v/' + stream_id + '_0-' + str(current_segment) + '.m4v'
    segment_audio_url = stream_server_directory + '/live-hd-a/' + stream_id + '_0-' + str(current_segment) + '.m4a'

    video_path = os.path.join(user_dir, str(live_username), 'Livestreams', str(stream_time), str(stream_id) + '_0-' + str(current_segment) + '.m4v')
    audio_path = os.path.join(user_dir, str(live_username), 'Livestreams', str(stream_time), str(stream_id) + '_0-' + str(current_segment) + '.m4a')

    if not os.path.isfile(video_path) and not os.path.isfile(audio_path):
        video = retry_network_wrapper(session.get, [segment_video_url])
        audio = retry_network_wrapper(session.get, [segment_audio_url])

        if video and audio:
            if len(video.content) > 0 and len(audio.content) > 0:
                formatted_print('LIVESTREAMS', str.format('Downloaded segment {} of broadcast by {}', current_segment, live_username))
                open(audio_path, 'wb').write(audio.content)
                open(video_path, 'wb').write(video.content)
                return True
        return False
    return True


# Wait for MPEG-DASH file to become available. If it does not become available, return False.
def await_dash(dash_url, session):
    retry_count = 0

    while session.get(dash_url).status_code != 200:
        if retry_count > 10:
            return False

        retry_count += 1
        time.sleep(1)

    return True


# Update the current_frame
def update_current_frame(dash_url):
    current_stream_dash = retry_wrapper(MPEGDASHParser.parse, [dash_url], 5, 1) #TODO: Make retry count user modifiable
    if current_stream_dash:
        current_frame = current_stream_dash.periods[0].adaptation_sets[0].representations[0].segment_templates[0].segment_timelines[0].Ss[len(current_stream_dash.periods[0].adaptation_sets[0].representations[0].segment_templates[0].segment_timelines[0].Ss) - 1].t
        offset = current_stream_dash.periods[0].adaptation_sets[0].representations[0].segment_templates[0].segment_timelines[0].Ss[len(current_stream_dash.periods[0].adaptation_sets[0].representations[0].segment_templates[0].segment_timelines[0].Ss) - 1].d
        return (current_stream_dash, current_frame, offset)

    return (None, 0, 2000)


# Check heartbeat
def heartbeat(stream_id, session):
    heartbeat = retry_network_wrapper(session.post, ['https://i.instagram.com/api/v1/live/' + stream_id + '/heartbeat_and_get_viewer_count/'], 10, 1, [200])
    if heartbeat:
        heartbeat_info = json.loads(heartbeat.text)
        return heartbeat_info['broadcast_status']

    return 'interrupted'


def go_backwards(stream_dash, dash_url, stream_directory, stream_time, stream_id, live_username, session, user_dir):
    offset_collection = []

    # Iterate through all offsets that are explicitly listed in the MPD
    for index, S in enumerate(stream_dash.periods[0].adaptation_sets[0].representations[0].segment_templates[0].segment_timelines[0].Ss):
        if S.d not in offset_collection:
            offset_collection.append(S.d)

    # Once the earliest segment is reached, brute-force with the last-known offset from there
    # For this, test every offset collected so far and eliminate all offsets that don't produce a correct response
    segment = stream_dash.periods[0].adaptation_sets[0].representations[0].segment_templates[0].segment_timelines[0].Ss[0].t

    while segment > 0:
        for offset in offset_collection:
            next_segment = segment - offset
            if next_segment < 0 or not grab_media(next_segment, stream_directory, stream_time, stream_id, live_username, session, user_dir):
                offset_collection.remove(offset)

        # Now, there should only be 0 or 1 offset in the offset_collection
        # If 0, break. If 1, continue with that offset
        if len(offset_collection) == 0:
            return
        else:
            segment -= offset_collection[0]


def go_forwards(stream_dash, dash_url, stream_directory, stream_time, stream_id, live_username, session, user_dir):
    while True:
        # Iterate through all segments listed in MPD
        for index, S in enumerate(stream_dash.periods[0].adaptation_sets[0].representations[0].segment_templates[0].segment_timelines[0].Ss):
            grab_media(S.t, stream_directory, stream_time, stream_id, live_username, session, user_dir)

        while True:
            # Check heartbeat
            broadcast_status = heartbeat(stream_id, session)

            # Handle heartbeat
            if broadcast_status == 'active':
                break
            elif broadcast_status == 'stopped' or broadcast_status == 'hard_stop':
                # Try to grab as many more segments as we can
                stream_dash, current_frame, current_offset = update_current_frame(dash_url)

                segment = current_frame + current_offset

                while grab_media(segment, stream_directory, stream_time, stream_id, live_username, session, user_dir):
                    segment += current_offset

                return
            time.sleep(1)

        time.sleep(1)
        stream_dash, current_frame, current_offset = update_current_frame(dash_url)


# Orchestrates the downloading process for a single stream
def grab_stream(broadcast, session, user_dir):
    # Grab broadcast information
    stream_id = broadcast['id']
    dash_url = broadcast['dash_playback_url']

    # Wait for MPEG-DASH file to become available
    if not await_dash(dash_url, session):
        return

    # Create a folder-friendly username
    live_username = sanitize_string(broadcast['broadcast_owner']['username'])

    formatted_print('LIVESTREAMS', str.format('Broadcast by {} found, downloading...', live_username))
    # Grab segment data
    stream_server_directory = dash_url.split('/dash-hd/')[0]
    current_stream_dash, current_frame, current_offset = update_current_frame(dash_url)

    # Initialize variables
    stream_time = str(current_stream_dash.availability_start_time).replace(':', '-')

    # Create save directory
    directory = os.path.join(user_dir, str(live_username), 'Livestreams', stream_time)
    if not os.path.isdir(directory):
        os.makedirs(directory)

    # Save the first available MPEG-DASH file
    first_dash = retry_network_wrapper(session.get, [dash_url])
    open(os.path.join(directory, 'mpegdash.mpd'), 'wb').write(first_dash.content)

    # Get initialization media
    initialization_video, initialization_audio = grab_initialization_media(stream_server_directory, stream_id, session)

    # Save initialization media
    open(os.path.join(directory, str(stream_id) + '_0-init.m4v'), 'wb').write(initialization_video.content)
    open(os.path.join(directory, str(stream_id) + '_0-init.m4a'), 'wb').write(initialization_audio.content)

    # Step 1: Grab current frame
    # Step 2: Spawn 2 threads
    # Step 3: Thread 1 works backwards from the current_frame value
    # Step 4: Thread 2 works forwards from the current_frame value in the expected manner
    try:
        backwards_process = multiprocessing.Process(target=go_backwards, args=(current_stream_dash, dash_url, stream_server_directory, stream_time, stream_id, live_username, session, user_dir))
        processes.append(backwards_process)
        backwards_process.start()

        forwards_process = multiprocessing.Process(target=go_forwards, args=(current_stream_dash, dash_url, stream_server_directory, stream_time, stream_id, live_username, session, user_dir))
        processes.append(forwards_process)
        forwards_process.start()

        backwards_process.join()
        forwards_process.join()

        # Mux and clean up
        mux_files(live_username, stream_time, stream_id, user_dir)

        current_broadcasts.remove(broadcast['id'])

    except (KeyboardInterrupt, SystemExit):
        for process in processes:
            process.terminate()

        # Mux and clean up
        mux_files(live_username, stream_time, stream_id, user_dir)

        sys.exit()
    except Exception as e:
        for process in processes:
            process.terminate()

        # Mux and clean up
        mux_files(live_username, stream_time, stream_id, user_dir)

# Muxes together video and audio stream segments
def mux_files(live_username, stream_time, stream_id, user_dir):
    # Setup paths
    output_path = os.path.join(user_dir, str(live_username), 'Livestreams', str(stream_time)) + '\\'
    output_init_path = output_path + str(stream_id) + '_0-init'
    filename = str(stream_time) + '.mp4'

    # Setup output files
    output_stream_audio = open(output_path + 'full.m4a', 'wb')
    output_stream_video = open(output_path + 'full.m4v', 'wb')

    shutil.copyfileobj(open(output_init_path + '.m4a', 'rb'), output_stream_audio)
    shutil.copyfileobj(open(output_init_path + '.m4v', 'rb'), output_stream_video)

    # Sort segments in natural order
    lst = natsorted(os.listdir(output_path))

    # Concatenate video and audio segments
    for x in lst:
        if 'init' in x or 'output' in x or 'full' in x:
            continue
        elif 'm4a' in x:
            shutil.copyfileobj(open(output_path + x, 'rb'), output_stream_audio)
        elif 'm4v' in x:
            shutil.copyfileobj(open(output_path + x, 'rb'), output_stream_video)

    output_stream_audio.close()
    output_stream_video.close()

    # Mux tracks
    ff = ffmpy.FFmpeg(
                inputs = {output_path + 'full.m4v' : None, output_path + 'full.m4a' : None},
                outputs = {output_path + filename : ['-y', '-c:a', 'copy', '-c:v', 'copy', '-hide_banner', '-loglevel', 'panic']}
    )
    ff.run()
    cleanup_files(lst, filename, output_path)
    formatted_print('LIVESTREAMS', str.format('Broadcast by {} successfully downloaded!', live_username))


# Delete all files except final output
def cleanup_files(lst, filename, output_path):
    for x in lst:
        if filename not in x:
            os.system('del ' + output_path + x)


# Continuously check live broadcasts, download broadcasts if not already in process of downloading.
def grab_live_videos(session, usernames, session_info, user_dir):
    formatted_print('LIVESTREAMS', 'Checking for broadcasts...')

    live_info = retry_network_wrapper(session.get, ['https://i.instagram.com/api/v1/live/reels_tray_broadcasts/'])

    try:
        live_info_json = json.loads(live_info.text)
    except Exception as e:
        formatted_print('LIVESTREAMS', 'Could not check broadcasts. Please ensure you are following at least one account.')
        return


    # Iterate through currently live broadcasts and spawn a thread to download the broadcast
    for broadcast in live_info_json['broadcasts']:
        grab_broadcast = broadcast['broadcast_owner']['username'] in usernames or len(usernames) == 0
        if broadcast['id'] not in current_broadcasts and grab_broadcast:
            broadcast_session = requests.Session()

            broadcast_session.headers.update(session_info[0])
            broadcast_session.cookies.update(session_info[1])

            broadcast_thread = threading.Thread(target=grab_stream, args=(broadcast, broadcast_session, user_dir))
            broadcast_thread.start()

            #TODO: Figure out how to get this to work with global variables (send() and recv())
            #broadcast_process = multiprocessing.Process(target=grab_stream, args=(broadcast, broadcast_session, user_dir))
            #broadcast_process.start()

            #processes.append(broadcast_process)
            current_broadcasts.append(broadcast['id'])

    formatted_print('LIVESTREAMS', 'Check complete!')


def run(sessions, cooldown, usernames_to_grab, user_dir):
    # App-ID is required to access the reels_tray_broadcasts
    # *Any* CSRFToken works at the moment, could be a bug? Gross negligence? Liability?
    # The code below will generate a random CSRF-Token but it is probably not recommended to use this
    # csrf_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    # print(csrf_token)

    session = sessions['desktop_auth']
    headers = {"X-IG-App-ID": "936619743392459", 'X-CSRFToken' : session.cookies['csrftoken']}
    session.headers.update(headers)

    while True:
        grab_live_videos(session, usernames_to_grab, (session.headers, session.cookies), user_dir)
        time.sleep(cooldown)

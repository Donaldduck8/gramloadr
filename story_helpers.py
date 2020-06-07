import os
from helpers import *
from mutagen.mp4 import MP4, MP4Cover
import piexif

def get_tappable_object(item, comment):
    if exists(item, ['tappable_objects']):
        tappable_objects = item['tappable_objects']

        # Iterate over all tappable objects, consider only tappable feed media
        for __i, object in enumerate(tappable_objects):
            if object['__typename'] == 'GraphTappableFeedMedia':
                if exists(object, ['media', 'shortcode']):
                    url = 'https://instagram.com/p/' + object['media']['shortcode']
                    comment += '[Embed] ' + url + '\n\n'

    return comment

def get_attribution_url(item, comment):
    if exists(item, ['story_app_attribution', 'content_url']):
        comment += '[Link]\n' + item['story_app_attribution']['content_url'] + '\n\n'

    return comment

def get_swipe(item, comment):
    if exists(item, ['story_cta_url']):
        comment += '[Swipe]\n' + item['story_cta_url'] + '\n\n'

    return comment

def get_story_music_stickers(item, save_path, session):
    if 'story_music_stickers' in item:
        for i, sticker in enumerate(item['story_music_stickers']):
            if exists(sticker, ['music_asset_info']):
                music_asset = sticker['music_asset_info']

                if exists(music_asset, ['display_artist']):
                    artist = music_asset['display_artist']

                if exists(music_asset, ['title']):
                    title = music_asset['title']

                if exists(music_asset, ['is_explicit']):
                    is_explicit = str(music_asset['is_explicit']) == 'True'

                if exists(music_asset, ['cover_artwork_uri']):
                    artwork_url = music_asset['cover_artwork_uri']
                    artwork_data = retry_network_wrapper(session.get, [artwork_url]).content

                if exists(music_asset, ['progressive_download_url']):
                    # Extract filename of story, reuse it for this audio
                    music_path = os.path.splitext(save_path)[0] + "_audio_" + str(i) + ".m4a"
                    music_url = music_asset['progressive_download_url']
                    music_data = retry_network_wrapper(session.get, [music_url]).content

                    with open(music_path, 'wb') as music_file:
                        music_file.write(music_data)

                    with open(music_path, 'rb') as music_file:
                        mutagen_file = MP4(music_path)
                        tags = mutagen_file.tags

                        if artist:
                            tags['\xa9ART'] = artist

                        if title:
                            tags['\xa9nam'] = title
                            tags['\xa9alb'] = title

                        if is_explicit:
                            tags['rtng'] = [1]

                        if artwork_data:
                            tags['covr'] = [MP4Cover(artwork_data, imageformat=MP4Cover.FORMAT_JPEG)]

                        tags.save(music_path)

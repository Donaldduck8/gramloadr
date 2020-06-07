import re
import sys
import json
import time
import math
import datetime
from natsort import natsorted
import piexif

debug = False
counter = 0

def partition_list(list, partition_size):
    partition_count = math.ceil(len(list) / partition_size)
    partitioned_list = []

    for i in range(partition_count):
        index_from = i * partition_size
        index_to = index_from + min(partition_size, len(list) - index_from)

        partitioned_list.append(list[index_from : index_to])

    return partitioned_list


def construct_queryhash_url(query_hash, **kwargs):
    variables = str(kwargs)

    # Format URL, insert query hash and variables, force double quotes and lower case.
    url = str.format('https://www.instagram.com/graphql/query/?query_hash={}&variables={}', query_hash, variables)
    url = url.replace('\'', '\"').replace(' ', '')
    return url


# A wrapper for any function that needs to be safely handled on miscellaneous exceptions.
def retry_wrapper(func, args=[], retry_count_limit=3, sleep_time=1):
    retry_count = 0
    while retry_count < retry_count_limit:
        try:
            if debug:
                print(args[0])
            return func(*args)
        except Exception as e:
            print(e)
            retry_count += 1
            time.sleep(sleep_time)
    return False


# A wrapper for any function that needs to be safely handled on occasional network drops.
def retry_network_wrapper(func, args=[], retry_count_limit=3, sleep_amount=1, valid_status_codes=[200]):
    global counter
    retry_count = 0
    while retry_count < retry_count_limit:
        try:
            #counter += 1
            #print('Request #', str(counter))
            if debug:
                print(args[0])
            r = func(*args)
            if r.status_code not in valid_status_codes:
                print(int(datetime.datetime.now().timestamp()))
                print('Status code not in valid parameters: ' + str(r.status_code))
                print('URL: ' + args[0])
                raise Exception('Request in network_wrapper failed!')
                print(r.text)
            return r
        except Exception as e:
            print(e)
            retry_count += 1
            time.sleep(sleep_amount)
    print(int(datetime.datetime.now().timestamp()))
    print('retry_network_wrapper died')
    print('URL: ' + args[0])
    return None


# Create a string representing the uint values of the UTF-16 byte representation
# of the supplied string. This is used to write comments to EXIF fields.
def unicode_byte_string(string):
    bytes = string.encode('UTF-16')[2:]

    byte_string = ''
    for byte in bytes:
        byte_string += str(int(byte)) + ' '

    byte_string += '0 0'
    return byte_string


def unicode_byte_tuple(string):
     return tuple(map(int, unicode_byte_string(string).split(' ')))


def set_comment(file_path, comment):
    #Load EXIF tags into dictionary
    exif_dict = piexif.load(file_path)

    # Prepare weird-ass formatting that piexiv expects for strings
    formatted_comment = unicode_byte_tuple(comment)

    # The field XPComments which is where comments are stored on Windows is stored at offset 40092
    exif_dict['0th'][40092] = formatted_comment

    # Dump EXIF tags
    exif_bytes = piexif.dump(exif_dict)

    # Write EXIF tags
    piexif.insert(exif_bytes, file_path)


def grab_following_ids(own_user_id, usernames_to_grab, session):
    #TODO Might have to fix this where it only returns up to 50 edges per request

    following_url = construct_queryhash_url('d04b0a864b4b54837c0d870b0e77e076', id=str(own_user_id), first=10000)
    user_following = json.loads(session.get(following_url).text)

    # Resets the array so it doesn't grow with each iteration
    user_following_ids = []

    for edge in user_following['data']['user']['edge_follow']['edges']:
        if edge['node']['username'] in usernames_to_grab or not usernames_to_grab:
            user_following_ids.append(edge['node']['id'])

    return natsorted(user_following_ids)

def grab_following_ids_and_names(own_user_id, usernames_to_grab, session):
    following_url = construct_queryhash_url('d04b0a864b4b54837c0d870b0e77e076', id=str(own_user_id), first=10000)
    user_following = json.loads(session.get(following_url).text)

    # Resets the array so it doesn't grow with each iteration
    user_following_users_and_ids = []

    for edge in user_following['data']['user']['edge_follow']['edges']:
        if edge['node']['username'] in usernames_to_grab or not usernames_to_grab:
            user_following_users_and_ids.append((edge['node']['id'], edge['node']['username']))

    return natsorted(user_following_users_and_ids)


# Remove characters which are forbidden in Windows file and folder names
def sanitize_string(string):
    forbidden_characters_regex = '[<>:"\/\\|\?\*]'
    sanitized_string = re.sub(forbidden_characters_regex, '', string)
    return sanitized_string


def exists(object={}, args=[]):
    pointer = object
    for key in args:
        if key in pointer and pointer[key] is not None:
            pointer = pointer[key]
        else:
            return False
    return True

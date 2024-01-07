import os
import random
import hashlib
import subprocess
from pprint import pprint
from datatypes import PathAndCreationTime
from constants import *

def get_file_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as file:
        while chunk := file.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()[:32]


def get_file_mime_type(file_path):
    result = subprocess.run(['file', '--brief', '--mime', file_path], capture_output=True, text=True)
    return result.stdout.strip()


def rename_files_with_hash(directory):
    for folder_path, _, file_names in os.walk(directory):
        for file_name in file_names:
            file_path = os.path.join(folder_path, file_name)

            # Get SHA256 hash (truncated at 32 characters)
            file_hash = get_file_sha256(file_path)

            # Get Linux file type
            mime_type = get_file_mime_type(file_path)

            # Extract file extension from mime type
            file_extension = mime_type.split('/')[-1].replace("; charset=binary", "")

            # Construct new file name
            new_file_name = f"{file_hash}.{file_extension}"

            # Rename the file
            new_file_path = os.path.join(folder_path, new_file_name)
            os.rename(file_path, new_file_path)

            print(f"Renamed: {file_path} to {new_file_path}")


def rename_xm4v_to_mp4(directory):
    for folder_path, _, file_names in os.walk(directory):
        for file_name in file_names:
            if file_name.endswith('.x-m4v'):
                file_path = os.path.join(folder_path, file_name)

                # Construct new file name with "mp4" extension
                new_file_name = os.path.splitext(file_name)[0] + '.mp4'

                # Rename the file
                new_file_path = os.path.join(folder_path, new_file_name)
                os.rename(file_path, new_file_path)

                print(f"Renamed: {file_path} to {new_file_path}")


def remove_duplicate_jpeg_files(directory):
    for folder_path, _, file_names in os.walk(directory):
        for file_name in file_names:
            if file_name.lower().endswith('.jpeg'):
                jpeg_file_path = os.path.join(folder_path, file_name)

                # Check if a corresponding "jpg" file exists
                jpg_file_name = file_name.lower().replace('.jpeg', '.jpg')
                jpg_file_path = os.path.join(folder_path, jpg_file_name)

                if os.path.exists(jpg_file_path):
                    # Remove the "jpeg" file
                    os.remove(jpeg_file_path)
                    print(f"Removed: {jpeg_file_path} (due to existing {jpg_file_path})")


def all_hentai_files():
    hentai = []
    for root, dirs, file in os.walk(f"{os.getcwd()}/download"):
        for name in file:
            if name not in hentai and name.lower().endswith(("png", "jpg", "jpeg", "gif", "mp4")):
                hentai.append(os.path.join(root, name))
    return hentai


def load_nsfw_paths_and_ctimes(directory):
    file_list = []

    for folder_path, _, file_names in os.walk(directory):
        for file_name in file_names:
            file_path = os.path.join(folder_path, file_name)

            # Check if it's a file (not a directory) and if it is media
            if os.path.isfile(file_path) and file_name.lower().endswith(("png", "jpg", "jpeg", "gif", "mp4")):
                # Get the creation time of the file in Unix seconds
                created_at = os.path.getctime(file_path)

                # Create a PathAndCreationTime object and add it to the list
                file_info = PathAndCreationTime(file_path, created_at)
                file_list.append(file_info)

    file_list.sort(key=lambda x: x.created_at, reverse=True)

    return file_list


def choose_image(catalog, new, limit):
    if not new:
        return random.choice(catalog).path
    else:
        return random.choice(catalog[:limit]).path


if __name__ == "__main__":
    for item in load_nsfw_paths_and_ctimes(NSFW_SOURCE_PATH):
        print(item)
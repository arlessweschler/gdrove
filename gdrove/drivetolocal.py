from gdrove.common import process_recursively
from gdrove.helpers import pretty_size
from googleapiclient.http import MediaIoBaseDownload
from datetime import datetime, timedelta
import progressbar
import pytz
import os


def download_file(drive, sourceid, dest, filename, filesize):

    request = drive.files().get_media(fileId=sourceid)
    dest_file = dest / filename
    with open(dest_file, 'wb') as f, progressbar.ProgressBar(max_value=filesize, widgets=[f'downloading {dest_file.as_posix()} ', progressbar.AdaptiveTransferSpeed(), ' ', progressbar.Bar(), ' ', progressbar.AdaptiveETA()]) as pbar:
        downloader = MediaIoBaseDownload(f, request, chunksize=1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk(num_retries=3)
            if status:
                pbar.update(status.resumable_progress)


def compare_function(drive, source_file, dest_file, dest_dir):
    if source_file['name'] == dest_file.name:
        dest_file_mod_time = datetime.utcfromtimestamp(
            dest_file.stat().st_mtime)
        dest_file_mod_time_tz = dest_file_mod_time.replace(tzinfo=pytz.UTC)
        source_file_mod_time = datetime.fromisoformat(
            source_file['modtime'][:-1] + '+00:00')

        # deal with low-precision time
        source_file_mod_time -= timedelta(microseconds=source_file_mod_time.microsecond)
        dest_file_mod_time_tz -= timedelta(microseconds=dest_file_mod_time_tz.microsecond)
        if source_file_mod_time > dest_file_mod_time_tz:
            return True, (source_file['id'], dest_dir, source_file['name'], source_file['size']), None
        return True, None, None
    return False, None, None


def new_folder_function(_, folder_name, folder_parent):

    dest_folder = folder_parent / folder_name
    dest_folder.mkdir(parents=True)
    return dest_folder


def sync(drive, sourceid, dest):

    download_jobs, delete_jobs = process_recursively(
        drive, sourceid, dest, compare_function, new_folder_function)

    if len(download_jobs) > 0:
        for i in download_jobs:
            download_file(drive, i[0], i[1], i[2], i[3])
    else:
        print('nothing to upload')

    if len(delete_jobs) > 0:
        print('calculating file sizes...')
        total_size = 0
        total_files = 0
        total_folders = 0
        for i in delete_jobs:
            if i[0].is_file():
                total_size += i[0].stat().st_size
                total_files += 1
            elif i[0].is_dir():
                total_folders += 1
        yn = input(
            f"{len(total_files)} files and {len(total_folders)} folders queued for deletion, totalling {pretty_size(total_size)}. Are you sure you'd like to delete them? [Y/n] ").lower().strip()
        if len(yn) > 0 and yn[0] == 'n':
            print('cancelling deletion jobs...')
        else:
            for i in progressbar.progressbar(delete_jobs, widgets=['deleting files ', progressbar.Counter(), '/' + str(len(delete_jobs)), ' ', progressbar.Bar(), ' ', progressbar.AdaptiveETA()]):
                os.remove(i[0])
    else:
        print('nothing to delete')

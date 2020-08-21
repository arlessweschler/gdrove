from gdrove.common import process_recursively
from gdrove.helpers import apicall
from googleapiclient.http import MediaFileUpload
from datetime import datetime, timedelta
import progressbar
import pytz


def get_time_rfc3339(source_file):
    source_file_mod_time = datetime.utcfromtimestamp(
        source_file.stat().st_mtime)
    return source_file_mod_time.isoformat() + 'Z'


def upload_resumable(drive, to_upload, parent):

    filesize = to_upload.stat().st_size

    media = MediaFileUpload(to_upload, resumable=True, chunksize=1024 * 1024)
    request = drive.files().create(media_body=media, supportsAllDrives=True, body={
        'name': to_upload.name,
        'parents': [parent],
        'modifiedTime': get_time_rfc3339(to_upload)
    })

    response = None
    with progressbar.ProgressBar(max_value=filesize, widgets=[f'uploading {to_upload.as_posix()} ', progressbar.AdaptiveTransferSpeed(), ' ', progressbar.Bar(), ' ', progressbar.AdaptiveETA()]) as pbar:
        while response is None:
            status, response = request.next_chunk()
            if status:
                pbar.update(status.resumable_progress)

    return response


def upload_multipart(drive, to_upload, parent):

    media = MediaFileUpload(to_upload)
    request = drive.files().create(media_body=media, supportsAllDrives=True, body={
        'name': to_upload.name,
        'parents': [parent],
        'modifiedTime': get_time_rfc3339(to_upload)
    })
    print(f'uploading {to_upload.as_posix()}')
    resp = apicall(request)

    return resp


def compare_function(drive, source_file, dest_file, dest_dir):

    if source_file.name == dest_file['name']:
        source_file_mod_time = datetime.utcfromtimestamp(
            source_file.stat().st_mtime)
        source_file_mod_time_tz = source_file_mod_time.replace(tzinfo=pytz.UTC)
        dest_file_mod_time = datetime.fromisoformat(
            dest_file['modtime'][:-1] + '+00:00')

        # deal with low-precision time
        source_file_mod_time_tz -= timedelta(microseconds=source_file_mod_time_tz.microsecond)
        dest_file_mod_time -= timedelta(microseconds=dest_file_mod_time.microsecond)
        if source_file_mod_time_tz > dest_file_mod_time:
            return True, (source_file, dest_dir), dest_file['id']
        else:
            return True, None, None
    return False, None, None


def new_folder_function(drive, folder_name, folder_parent):

    return apicall(drive.files().create(body={
        'mimeType': 'application/vnd.google-apps.folder',
        'name': folder_name,
        'parents': [folder_parent]
    }, supportsAllDrives=True))['id']


def sync(drive, source, destid):

    upload_jobs, delete_jobs = process_recursively(
        drive, source, destid, compare_function, new_folder_function)

    if len(upload_jobs) > 0:
        for i in upload_jobs:
            filesize = i[0].stat().st_size
            if filesize == 0:
                apicall(drive.files().create(body={
                    'name': i[0].name,
                    'parents': [i[1]]
                }))
            elif filesize <= 5242880:
                upload_multipart(drive, i[0], i[1])
            else:
                upload_resumable(drive, i[0], i[1])
    else:
        print('nothing to upload')

    if len(delete_jobs) > 0:
        for i in progressbar.progressbar(delete_jobs, widgets=['deleting files ', progressbar.Counter(), '/' + str(len(delete_jobs)), ' ', progressbar.Bar(), ' ', progressbar.AdaptiveETA()]):
            apicall(drive.files().delete(fileId=i, supportsAllDrives=True))
    else:
        print('nothing to delete')

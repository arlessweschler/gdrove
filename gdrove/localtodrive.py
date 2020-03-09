from gdrove.helpers import lsfiles, lsfolders, get_files, apicall
from googleapiclient.http import MediaFileUpload
from pathlib import Path
from datetime import datetime
import progressbar, pytz

def get_time_rfc3339(source_file: Path):
    source_file_mod_time = datetime.utcfromtimestamp(source_file.stat().st_mtime)
    return source_file_mod_time.isoformat() + "Z"

def upload_resumable(drive, to_upload: Path, parent):
    
    filesize = to_upload.stat().st_size

    media = MediaFileUpload(to_upload, resumable=True, chunksize=1024 * 1024)
    request = drive.files().create(media_body=media, supportsAllDrives=True, body={
        "name": to_upload.name,
        "parents": [parent],
        "modifiedTime": get_time_rfc3339(to_upload)
    })

    response = None
    with progressbar.ProgressBar(max_value=filesize, widgets=[f"uploading {to_upload.as_posix()} ", progressbar.AdaptiveTransferSpeed(), " ", progressbar.Bar(), " ", progressbar.AdaptiveETA()]) as pbar:
        while response is None:
            status, response = request.next_chunk()
            if status:
                pbar.update(status.resumable_progress)

    return response

def upload_multipart(drive, to_upload, parent):
    
    media = MediaFileUpload(to_upload)
    request = drive.files().create(media_body=media, supportsAllDrives=True, body={
        "name": to_upload.name,
        "parents": [parent],
        "modifiedTime": get_time_rfc3339(to_upload)
    })
    print(f"uploading {to_upload.as_posix()}")
    resp = apicall(request)

    return resp

def sync(drive, source, destid):

    to_process = set()
    to_process.add((source, destid))

    upload_jobs = set()
    delete_jobs = set()

    while len(to_process) > 0:

        print(f"{len(to_process)} folders is queue")

        currently_processing = to_process.pop()

        source_folders = [i for i in currently_processing[0].iterdir() if i.is_dir()]
        dest_folders = lsfolders(drive, currently_processing[1])

        folders_to_delete = set()

        for source_folder in source_folders:
            for dest_folder in dest_folders:
                if source_folder.name == dest_folder["name"]:
                    to_process.add((source_folder, dest_folder["id"]))
                    break
            else:
                print(f"creating new directory \"{source_folder.name}\" in {currently_processing[1]}")
                to_process.add((source_folder, apicall(drive.files().create(body={
                    "mimeType": "application/vnd.google-apps.folder",
                    "name": source_folder.name,
                    "parents": [currently_processing[1]]
                }, supportsAllDrives=True))["id"]))
        
        for dest_folder in dest_folders:
            for source_folder in source_folders:
                if source_folder.name == dest_folder["name"]:
                    break
            else:
                folders_to_delete.add((dest_folder["id"], "foldernotinsource"))

        to_upload, to_delete = sync_directory(drive, currently_processing[0], currently_processing[1])
        to_delete.update(folders_to_delete)

        upload_jobs.update(to_upload)
        delete_jobs.update(to_delete)
    
    if len(upload_jobs) > 0:
        for i in upload_jobs:
            filesize = i[0].stat().st_size
            if filesize == 0:
                apicall(drive.files().create(body={
                    "name": i[0].name,
                    "parents": [i[1]]
                }))
            elif filesize <= 5242880:
                upload_multipart(drive, i[0], i[1])
            else:
                upload_resumable(drive, i[0], i[1])
    else:
        print("nothing to upload")

    if len(delete_jobs) > 0:
        for i in progressbar.progressbar(delete_jobs, widgets=["deleting files ", progressbar.Counter(), "/" + str(len(delete_jobs)), " ", progressbar.Bar(), " ", progressbar.AdaptiveETA()]):
            apicall(drive.files().delete(fileId=i[0], supportsAllDrives=True))
    else:
        print("nothing to delete")

def sync_directory(drive, source, destid):

    source_files = [i for i in Path(source).iterdir() if not i.is_dir()]
    dest_files = get_files(drive, destid)

    to_upload = set()
    to_delete = set()

    to_process_length = len(source_files) + len(dest_files)
    count = 0
    with progressbar.ProgressBar(0, to_process_length, ["processing files (" + source.name + ") ", progressbar.Counter(), "/" + str(to_process_length), " ", progressbar.Bar()]).start() as pbar:
        for source_file in source_files:
            for dest_file in dest_files:
                if source_file.name == dest_file["name"]:
                    source_file_mod_time = datetime.utcfromtimestamp(source_file.stat().st_mtime)
                    source_file_mod_time_tz = source_file_mod_time.replace(tzinfo=pytz.UTC)
                    dest_file_mod_time = datetime.fromisoformat(dest_file["modtime"][:-1] + "+00:00")
                    if source_file_mod_time_tz > dest_file_mod_time:
                        to_delete.add((dest_file["id"], "outdated"))
                        to_upload.add((source_file, destid))
                        break
                    else:
                        break
            else:
                to_upload.add((source_file, destid))
            count += 1
            pbar.update(count)
        
        for dest_file in dest_files:
            for source_file in source_files:
                if source_file.name == dest_file["name"]:
                    break
            else:
                to_delete.add((dest_file["id"], "notinsource"))
            count += 1
            pbar.update(count)
    
    return to_upload, to_delete
from gdrove.helpers import lsfiles, lsfolders, get_files, apicall, pretty_size
from googleapiclient.http import MediaIoBaseDownload
from pathlib import Path
from datetime import datetime
import progressbar, pytz, os

def download_file(drive, sourceid, dest, filename, filesize):

    request = drive.files().get_media(fileId=sourceid)
    dest_file = dest / filename
    with open(dest_file, "wb") as f, progressbar.ProgressBar(max_value=filesize, widgets=[f"downloading {dest_file.as_posix()} ", progressbar.AdaptiveTransferSpeed(), " ", progressbar.Bar(), " ", progressbar.AdaptiveETA()]) as pbar:
        downloader = MediaIoBaseDownload(f, request, chunksize=1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk(num_retries=3)
            if status:
                pbar.update(status.resumable_progress)

def sync(drive, sourceid, dest):

    to_process = set()
    to_process.add((sourceid, dest))

    download_jobs = set()
    delete_jobs = set()

    while len(to_process) > 0:

        print(f"{len(to_process)} folders is queue")

        currently_processing = to_process.pop()

        source_folders = lsfolders(drive, currently_processing[0])
        dest_folders = [i for i in currently_processing[1].iterdir() if i.is_dir()]

        folders_to_delete = set()

        for source_folder in source_folders:
            for dest_folder in dest_folders:
                if source_folder["name"] == dest_folder.name:
                    to_process.add((source_folder["id"], dest_folder))
                    break
            else:
                print(f"creating new directory \"{source_folder['name']}\" in {currently_processing[1].as_posix()}")
                dest_folder = dest / source_folder["name"]
                dest_folder.mkdir(parents=True)
                to_process.add((source_folder["id"], dest_folder))
        
        for dest_folder in dest_folders:
            for source_folder in source_folders:
                if source_folder["name"] == dest_folder.name:
                    break
            else:
                folders_to_delete.add((dest_folder, "foldernotinsource"))

        to_download, to_delete = sync_directory(drive, currently_processing[0], currently_processing[1])
        to_delete.update(folders_to_delete)

        download_jobs.update(to_download)
        delete_jobs.update(to_delete)
    
    if len(download_jobs) > 0:
        for i in download_jobs:
            download_file(drive, i[0], i[1], i[2], i[3])
    else:
        print("nothing to upload")

    if len(delete_jobs) > 0:
        print("calculating file sizes...")
        total_size = 0
        total_files = 0
        total_folders = 0
        for i in delete_jobs:
            if i[0].is_file():
                total_size += i[0].stat().st_size
                total_files += 1
            elif i[0].is_dir():
                total_folders += 1
        yn = input(f"{len(total_files)} files and {len(total_folders)} folders queued for deletion, totalling {pretty_size(total_size)}. Are you sure you'd like to delete them? [Y/n] ").lower().strip()
        if len(yn) > 0 and yn[0] == "n":
            print("cancelling deletion jobs...")
        else:
            for i in progressbar.progressbar(delete_jobs, widgets=["deleting files ", progressbar.Counter(), "/" + str(len(delete_jobs)), " ", progressbar.Bar(), " ", progressbar.AdaptiveETA()]):
                os.remove(i[0])
    else:
        print("nothing to delete")

def sync_directory(drive, sourceid, dest):

    source_files = get_files(drive, sourceid)
    dest_files = [i for i in Path(dest).iterdir() if not i.is_dir()]

    to_download = set()
    to_delete = set()

    to_process_length = len(source_files) + len(dest_files)
    count = 0
    with progressbar.ProgressBar(0, to_process_length, ["processing files (" + dest.name + ") ", progressbar.Counter(), "/" + str(to_process_length), " ", progressbar.Bar()]).start() as pbar:
        for source_file in source_files:
            for dest_file in dest_files:
                if source_file["name"] == dest_file.name:
                    dest_file_mod_time = datetime.utcfromtimestamp(dest_file.stat().st_mtime)
                    dest_file_mod_time_tz = dest_file_mod_time.replace(tzinfo=pytz.UTC)
                    source_file_mod_time = datetime.fromisoformat(source_file["modtime"][:-1] + "+00:00")
                    if source_file_mod_time > dest_file_mod_time_tz:
                        to_download.add((source_file["id"], dest, source_file["name"], source_file["size"]))
                        break
                    else:
                        break
            else:
                to_download.add((source_file["id"], dest, source_file["name"], source_file["size"]))
            count += 1
            pbar.update(count)
        
        for dest_file in dest_files:
            for source_file in source_files:
                if source_file["name"] == dest_file.name:
                    break
            else:
                to_delete.add((dest_file, "notinsource"))
            count += 1
            pbar.update(count)
    
    return to_download, to_delete
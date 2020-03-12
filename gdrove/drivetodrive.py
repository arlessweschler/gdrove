from gdrove.helpers import get_files, lsfolders, apicall, determine_folder
import progressbar

def compare_function(drive, source_file, dest_file) -> bool:
    if source_file["name"] == dest_file["name"]:
        if source_file["md5"] == dest_file["md5"]:
            return False
        else:
            return True

def delete_compare_function(drive, source_file, dest_file) -> bool:
    if source_file["name"] == dest_file["name"]:
        return True
    else:
        return False

def sync(drive, sourceid, destid):

    to_process = set()
    to_process.add((sourceid, destid))

    copy_jobs = set()
    delete_jobs = set()

    while len(to_process) > 0:

        print(f"{len(to_process)} folders is queue")

        currently_processing = to_process.pop()

        source_folders = lsfolders(drive, currently_processing[0])
        dest_folders = lsfolders(drive, currently_processing[1])

        folders_to_delete = set()

        for source_folder in source_folders:
            for dest_folder in dest_folders:
                if source_folder["name"] == dest_folder["name"]:
                    to_process.add((source_folder["id"], dest_folder["id"]))
                    break
            else:
                print(f"creating new directory \"{source_folder['name']}\" in {currently_processing[1]}")
                to_process.add((source_folder["id"], apicall(drive.files().create(body={
                    "mimeType": "application/vnd.google-apps.folder",
                    "name": source_folder["name"],
                    "parents": [currently_processing[1]]
                }, supportsAllDrives=True))["id"]))
        
        for dest_folder in dest_folders:
            for source_folder in source_folders:
                if source_folder["name"] == dest_folder["name"]:
                    break
            else:
                folders_to_delete.add(dest_folder["id"])

        to_copy, to_delete = determine_folder(drive, currently_processing[0], currently_processing[1], compare_function, delete_compare_function)
        to_delete.update(folders_to_delete)

        copy_jobs.update(set([(i, currently_processing[1]) for i in to_copy]))
        delete_jobs.update(to_delete)
    
    if len(copy_jobs) > 0:
        for i in progressbar.progressbar(copy_jobs, widgets=["copying files ", progressbar.Counter(), "/" + str(len(copy_jobs)), " ", progressbar.Bar(), " ", progressbar.AdaptiveETA()]):
            apicall(drive.files().copy(fileId=i[0], body={"parents": [i[1]]}, supportsAllDrives=True))
    else:
        print("nothing to copy")

    if len(delete_jobs) > 0:
        for i in progressbar.progressbar(delete_jobs, widgets=["deleting files ", progressbar.Counter(), "/" + str(len(delete_jobs)), " ", progressbar.Bar(), " ", progressbar.AdaptiveETA()]):
            apicall(drive.files().delete(fileId=i, supportsAllDrives=True))
    else:
        print("nothing to delete")

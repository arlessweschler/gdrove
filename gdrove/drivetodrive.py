from gdrove.helpers import get_files, lsfolders, apicall, determine_folder, process_recursively
import progressbar

def compare_function(drive, source_file, dest_file, dest_dir):
    if source_file["name"] == dest_file["name"]:
        if source_file["md5"] == dest_file["md5"]:
            return True, None, None
        return True, (source_file["id"], dest_dir), dest_file
    return False, None, None

def new_folder_function(drive, folder_name, folder_parent):

    return apicall(drive.files().create(body={
            "mimeType": "application/vnd.google-apps.folder",
            "name": folder_name,
            "parents": [folder_parent]
        }, supportsAllDrives=True))["id"]

def sync(drive, sourceid, destid):

    copy_jobs, delete_jobs = process_recursively(drive, sourceid, destid, compare_function, new_folder_function)
    
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

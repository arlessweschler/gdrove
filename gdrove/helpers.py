from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json, time, progressbar, hashlib

def get_drive(creds):
    return build("drive", "v3", credentials=creds)

def apicall(req):
    sleep_time = 2
    tries = 0
    resp = None
    while resp == None:
        try:
            resp = req.execute()
        except HttpError as e:
            print(e.error_details)
            if tries == 3:
                print("WARN request erroring, please wait up to 5 minutes")
            if tries == 7:
                print("ERR stopped retrying on error")
                raise e
                break
            # time.sleep(sleep_time)
            tries += 1
            sleep_time *= 2
    
    if resp:
        if tries > 3:
            print("INFO erroring request went through")
        return resp
    else:
        return None

def ls(drive, folderid, q="", message="directory"):

    resp = {"nextPageToken": None}
    files = []
    if q:
        q += " and "
    q += f"trashed = false and '{folderid}' in parents"

    i = 0
    with progressbar.ProgressBar(0, progressbar.UnknownLength, widgets=["listing " + message + " " + folderid + " ", progressbar.RotatingMarker()]).start() as pbar:
        while "nextPageToken" in resp:
            resp = apicall(drive.files().list(pageSize=1000, q=q, supportsAllDrives=True, fields="files(id,name,md5Checksum,modifiedTime)"))
            files += resp["files"]
            pbar.update(i)
            i += 1

    return files

def lsfiles(drive, folderid):

    return ls(drive, folderid, "mimeType != 'application/vnd.google-apps.folder'", "files in")

def lsfolders(drive, folderid):

    return ls(drive, folderid, "mimeType = 'application/vnd.google-apps.folder'", "folders in")

def lsdrives(drive):

    resp = {"nextPageToken": None}
    files = []

    while "nextPageToken" in resp:
        resp = apicall(drive.drives().list(pageSize=100))
        files += resp["drives"]

    return files

def get_files(drive, parent):

    return [{"id": i["id"], "name": i["name"], "md5": i["md5Checksum"], "modtime": i["modifiedTime"]} for i in lsfiles(drive, parent)]

# TODO: find some way to md5sum while uploading a file to double check that it uploaded with the correct md5
def md5sum(filename):
    md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(128 * md5.block_size), b''):
            md5.update(chunk)
    return md5.hexdigest()
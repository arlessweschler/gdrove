__version__ = "0.1.0"

from pathlib import Path
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from packaging import version
import json, time, progressbar

# -- config stuff --

config_path = Path.home() / ".config" / "gdrove"
if not config_path.exists():
    config_path.mkdir(parents=True)

default_config = {
    "version": __version__,
    "accounts": [],
    "path_aliases": []
}

config_file = config_path / "config.json"
if not config_file.exists():
    config_file.write_text(json.dumps(default_config))

with config_file.open("r") as f:
    config = json.load(f)

def save_config(config):
    try:
        config_str = json.dumps(config)
    except TypeError as e:
        print(f"ERR failed saving config! reason: {str(e)}")
    config_file.write_text(config_str)

if "version" not in config or "accounts" not in config or "path_aliases" not in config:
    yn = input("ERR corrupted config, regen? [Y/n] ")
    if len(yn) > 0 and yn.lower()[0] == "n":
        print("QUIT config corrupted!")
        exit(1)
    else:
        print("WARN regenerating config")
        config_file.write_text(json.dumps(default_config))
        with config_file.open("r") as f:
            config = json.load(f)
        save_config(config)

if config["version"] != __version__:
    config_version = version.parse(config["version"])
    program_version = version.parse(__version__)
    # handle any version migration

    if config_version > program_version:
        yn = input(f"ERR config version ({config_version}) newer than program version ({program_version})! continue? [Y/n] ")
        if len(yn) > 0 and yn.lower()[0] == "n":
            print("QUIT program old")
            exit(1)
        else:
            print("WARN downgrading config!")
    else:
        print(f"INFO updating config from {config_version} to {program_version}")

    config["version"] = __version__
    save_config(config)

# -- auth stuff --

authstore = {}
default_scopes = ["https://www.googleapis.com/auth/drive"]

if len(config["accounts"]) > 0:
    for i in progressbar.progressbar(config["accounts"], widgets=["processing accounts [", progressbar.Counter(), "/", str(len(config["accounts"])), "] ",  progressbar.Bar()]):
        auth_dict = json.loads(i["auth"])
        if i["type"] == "sa":
            creds = service_account.Credentials.from_service_account_info(auth_dict, scopes=default_scopes)
            authstore[i["name"]] = creds
        elif i["type"] == "user":
            creds = Credentials.from_authorized_user_info(auth_dict, scopes=default_scopes)
            creds.refresh(Request())
            i["token"] = creds.token
            save_config(config)
            authstore[i["name"]] = creds
        else:
            print(f'WARN unknown auth type "{i["type"]}"')
            config.remove(i)
            save_config(config)

def auth_get(name):
    if name in authstore:
        return authstore[name]
    else:
        return None

def auth_add_user(name, creds_dict, remote=False):
    flow = InstalledAppFlow.from_client_config(creds_dict, scopes=default_scopes)
    if remote:
        creds = flow.run_console()
    else:
        creds = flow.run_local_server()
    authstore[name] = creds
    config["accounts"].append({
        "name": name,
        "type": "user",
        "auth": creds.to_json()
    })
    save_config(config)
    return creds

def auth_file_user(name, creds_file, remote=False):
    with Path(creds_file).open("r") as f:
        return auth_add_user(name, json.load(f), remote=remote)

def auth_add_sa(name, creds_dict):
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=default_scopes)
    authstore[name] = creds
    config["accounts"].append({
        "name": name,
        "type": "sa",
        "auth": creds_dict
    })
    save_config(config)
    return creds

def auth_file_sa(name, creds_file):
    with Path(creds_file).open("r") as f:
        return auth_add_sa(name, json.load(f))

# -- api stuff --

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
                print(e.with_traceback())
                break
            time.sleep(sleep_time)
            tries += 1
            sleep_time *= 2
    
    if resp:
        if tries > 3:
            print("INFO erroring request went through")
        return resp
    else:
        return None

def ls(drive, folderid, q=""):

    resp = {"nextPageToken": None}
    files = []
    if q:
        q += " and "
    q += "trashed = false"

    with progressbar.ProgressBar(0, None, widgets=["listing directory " + folderid + " ", progressbar.RotatingMarker()]) as pbar:
        while "nextPageToken" in resp:
            resp = apicall(drive.files().list(pageSize=1000, parents=[folderid], q=q, supportsAllDrives=True))
            files += resp["files"]
            pbar.next()

    return files

def lsfiles(drive, folderid):

    return ls(drive, folderid, "mimeType != 'application/vnd.google-apps.folder'")

def lsfolders(drive, folderid):

    return ls(drive, folderid, "mimeType = 'application/vnd.google-apps.folder'")

def lsdrives(drive):

    resp = {"nextPageToken": None}
    files = []

    while "nextPageToken" in resp:
        resp = apicall(drive.drives().list(pageSize=100))
        files += resp["drives"]

    return files

def get_files(drive, parent):

    return [{"id": i["id"], "name": i["name"], "md5": i["md5Checksum"]} for i in lsfiles(drive, parent)]

# -- path stuff --

def get_path(path_string, creds):

    try:
        path_type, path_dirs = path_string.split("/")
    except ValueError:
        print("error processing path")
        return None

    if path_type == "ld":
        path_final = Path(path_dirs)
        if path_final.exists():
            return path_final
        else:
            print(f"path not found: {path_final.resolve()}")
            return None
    
    elif path_type in ["md", "sd", "fi"] or path_type in config["path_aliases"]:
    
        drive = get_drive(creds)
        to_traverse = path_dirs.split("/")
        to_traverse.reverse()

        if path_type == "md":
            current_dir = apicall(drive.files().get(fileId="root"))["id"]

        elif path_type == "sd":
            drives = lsdrives(drive)
            current_dir = None
            for i in drives:
                if i["name"] == to_traverse[-1]:
                    current_dir = i["id"]
                    break
            if current_dir == None:
                print("drive not found: " + to_traverse[-1])
                return None
            to_traverse.pop()

        elif path_type == "fi":
            current_dir = apicall(drive.files().get(fileId=to_traverse.pop()))["id"]
        
        else:
            current_dir = apicall(drive.files().get(fileId=config["path_aliases"][to_traverse.pop()]))["id"]
        
        while len(to_traverse) != 0:
            search_for = to_traverse.pop()
            found = False
            for i in ls(drive, current_dir):
                if i["name"] == search_for:
                    current_dir = i["id"]
                    found = True
                    break
            if not found:
                print(f"couldn't find {search_for}!")
                return None
            
        return current_dir
    
    else:
        print(f'unrecognized path type "{path_type}"')

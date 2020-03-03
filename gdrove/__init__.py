from pathlib import Path
from gdrove import helpers, drivetodrive
import json

def main(account_name, source_path, dest_path):

    creds = helpers.auth_get(account_name)
    if creds == None:
        creds_location = input("account not found. to add it, please input a path to the credentials of the account: ")
        account_path = Path(creds_location.strip())
        if not account_path.exists():
            print("file not found!")
            return -1
        with account_path.open("r") as f:
            account_data = json.load(f)
        if "type" in account_data and account_data["type"] == "service_account":
            creds = helpers.auth_add_sa(account_name, account_data)
        else:
            is_remote = input("are you on a headless server? [y/N] ").strip()[0].lower() == "y"
            creds = helpers.auth_add_user(account_name, account_data, remote=is_remote)

    drive = helpers.get_drive(creds)

    source_id = helpers.get_path(source_path)
    destination_id = helpers.get_path(source_path)

    if type(source_id) == str:
        from_drive = True
    else:
        from_drive = False
    
    if type(destination_id) == str:
        to_drive = True
    else:
        to_drive = False

    if from_drive and to_drive:
        drivetodrive.sync(drive, source_id, destination_id)
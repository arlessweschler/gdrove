from pathlib import Path
from gdrove import GDrove, get_drive, dtd, ltd, dtl
import argparse, json

gd = GDrove()

def do_new_user_account(args):

    gd.auth_add_user(args.name, args.creds, args.remote)

def do_new_service_account(args):

    gd.auth_add_sa(args.name, args.creds)

def do_remove_account(args):

    gd.auth_remove_account(args.name)

def do_list_accounts(args):

    for i in gd.auth_list_accounts():
        print(f'{i["name"]} ({i["type"]})')

def do_new_alias(args):

    creds = gd.auth_get(args.account)
    if creds == None:
        print(f"ERR account {args.account} not found!")
    else:
        gd.alias_add(args.name, args.path, creds)

def do_remove_alias(args):

    gd.alias_remove(args.name)

def do_list_alias(args):

    for i in gd.alias_list():
        print(f'{i["name"]} ({i["type"]}): {i["path"]}')

def do_sync(args):

    creds = gd.auth_get(args.account)
    if creds == None:
        return None

    drive = get_drive(creds)

    source_id = gd.get_path(args.source, creds)
    destination_id = gd.get_path(args.destination, creds)

    if type(source_id) == str:
        from_drive = True
    else:
        from_drive = False
    
    if type(destination_id) == str:
        to_drive = True
    else:
        to_drive = False

    if from_drive and to_drive:
        dtd(drive, source_id, destination_id)
    
    elif not from_drive and to_drive:
        ltd(drive, source_id, destination_id)
    
    elif from_drive and not to_drive:
        dtl(drive, source_id, destination_id)

def main():

    # main parser
    parser = argparse.ArgumentParser(prog="gdrove", description="GDrive tool to sync folders to/from/between GDrive folders")
    parser.set_defaults(do=None) # in case i miss something and the args don't set a function
    subparsers = parser.add_subparsers(title="actions")

    # config parser
    config_parser = subparsers.add_parser("config", description="Configure GDrove")
    config_subparsers = config_parser.add_subparsers()

    # account config parser
    account_config_parser = config_subparsers.add_parser("account", description="Add or remove accounts")
    account_config_subparsers = account_config_parser.add_subparsers()

    # user account config parser
    user_account_config_parser = account_config_subparsers.add_parser("user", description="Add user account")
    user_account_config_parser.add_argument("name", help="Name of account")
    user_account_config_parser.add_argument("--creds", "-c", default="credentials.json", help="Credentials to authenticate with")
    user_account_config_parser.add_argument("--remote", "-r", action="store_true", \
        help="Whether to authenticate using a local server. Only use if running from a headless server.")
    user_account_config_parser.set_defaults(do=do_new_user_account)

    # service account config parser
    service_account_config_parser = account_config_subparsers.add_parser("sa", description="Add service account")
    service_account_config_parser.add_argument("name", help="Name of account")
    service_account_config_parser.add_argument("file", help="Path to service account file")
    service_account_config_parser.set_defaults(do=do_new_service_account)

    # remove account config parser
    remove_account_config_parser = account_config_subparsers.add_parser("remove", description="Remove account")
    remove_account_config_parser.add_argument("name", help="Name of account")
    remove_account_config_parser.set_defaults(do=do_remove_account)

    # remove account config parser
    remove_account_config_parser = account_config_subparsers.add_parser("list", description="List accounts")
    remove_account_config_parser.set_defaults(do=do_list_accounts)
    
    # alias config parser
    alias_config_parser = config_subparsers.add_parser("alias", description="Add path alias")
    alias_config_subparsers = alias_config_parser.add_subparsers()

    # add alias config parser
    add_alias_config_parser = alias_config_subparsers.add_parser("new", description="Create new alias")
    add_alias_config_parser.add_argument("name", help="Name of alias")
    add_alias_config_parser.add_argument("path", help="Path to alias")
    add_alias_config_parser.add_argument("account", help="Account to resolve alias")
    add_alias_config_parser.set_defaults(do=do_new_alias)

    # remomve alias config parser
    remove_alias_config_parser = alias_config_subparsers.add_parser("remove", description="Remove alias")
    remove_alias_config_parser.add_argument("name", help="Name of alias")
    remove_alias_config_parser.set_defaults(do=do_remove_alias)

    # list alias config parser
    list_alias_config_parser = alias_config_subparsers.add_parser("list", description="List aliases")
    list_alias_config_parser.set_defaults(do=do_list_alias)

    # sync parser
    sync_parser = subparsers.add_parser("sync", description="Sync folders")
    sync_parser.add_argument("account", help="Name of account")
    sync_parser.add_argument("source", help="Path to source")
    sync_parser.add_argument("destination", help="Path to destination")
    sync_parser.add_argument("--yes", "-y", help="Force delete local files")
    sync_parser.set_defaults(do=do_sync)

    # parse
    args = parser.parse_args()
    if args.do != None:
        args.do(args)
    else:
        print("Please run with -h to see help.")

if __name__ == "__main__":
    main()
import argparse

def do_new_user_account(args):

    print(args)

def do_new_service_account(args):

    print(args)

def do_remove_account(args):

    print(args)

def do_new_alias(args):

    print(args)

def do_remove_alias(args):

    print(args)

def do_sync(args):

    print(args)

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
    
    # alias config parser
    alias_config_parser = config_subparsers.add_parser("alias", description="Add path alias")
    alias_config_parser.add_argument("name", help="Name of alias")
    alias_config_parser.add_argument("path", help="Path to alias")
    alias_config_parser.set_defaults(do=do_new_alias)

    # unalias config parser
    unalias_config_parser = config_subparsers.add_parser("unalias", description="Remove path alias")
    unalias_config_parser.add_argument("name", help="Name of alias")
    unalias_config_parser.set_defaults(do=do_remove_alias)

    # sync parser
    sync_parser = subparsers.add_parser("sync", description="Sync folders")
    sync_parser.add_argument("account", help="Name of account")
    sync_parser.add_argument("source", help="Path to source")
    sync_parser.add_argument("destination", help="Path to destination")
    sync_parser.set_defaults(do=do_sync)

    # parse
    args = parser.parse_args()
    if args.do != None:
        import gdrove
        args.do(args)
    else:
        print("Please run with -h to see help.")

if __name__ == "__main__":
    main()
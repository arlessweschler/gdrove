__version__ = '1.1.0'

from pathlib import Path
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from packaging import version
from gdrove.helpers import apicall, get_drive, ls, lsdrives
import json

_default_config = {
    'version': __version__,
    'accounts': [],
    'path_aliases': {}
}

_default_scopes = ['https://www.googleapis.com/auth/drive']


class GDrove:

    def __init__(self, config_path=Path.home()/'.config'/'gdrove', force=False, silent=False):

        self.config_path = config_path
        self.force = force
        self.silent = silent
        self.authstore = {}

        if not config_path.exists():
            config_path.mkdir(parents=True)

        config_file = config_path/'config.json'
        if not config_file.exists():
            config_file.write_text(json.dumps(_default_config))

        with config_file.open('r') as f:
            self.config = json.load(f)

        if 'version' not in self.config or 'accounts' not in self.config or 'path_aliases' not in self.config or \
                not isinstance(self.config['version'], str) or not isinstance(self.config['accounts'], list) or \
                not isinstance(self.config['path_aliases'], dict):
            if self.confirm('ERR corrupted config, regen? [Y/n] ', 'n'):
                self.log('WARN regenerating config')
                self.overwrite_config()
                with config_file.open('r') as f:
                    self.config = json.load(f)
            else:
                self.log('QUIT config corrupted!')
                exit(1)

        if self.config['version'] != __version__:
            config_version = version.parse(self.config['version'])
            program_version = version.parse(__version__)
            # handle any version migration

            if config_version > program_version:
                if self.confirm(f'ERR config version ({config_version}) newer than program version ({program_version})! continue? [Y/n] ', 'n'):
                    self.log('WARN downgrading config!')
                else:
                    self.log('QUIT program old')
                    exit(1)
            else:
                self.log(
                    f'INFO updating config from {config_version} to {program_version}')

            self.config['version'] = __version__
            self.save_config()

    def get_path(self, path_string, creds):

        try:
            path_type, path_dirs = path_string.split(':')
        except ValueError:
            print('error processing path')
            return None

        if path_type == 'ld':
            path_final = Path(path_dirs)
            if path_final.exists():
                return path_final
            else:
                print(f'path not found: {path_final.resolve()}')
                return None

        elif path_type in ['md', 'sd', 'fi'] or path_type in self.config['path_aliases']:

            drive = get_drive(creds)
            to_traverse = [i.strip() for i in path_dirs.strip('/').split('/')]
            to_traverse.reverse()

            if path_type == 'md':
                current_dir = apicall(drive.files().get(fileId='root'))['id']

            elif path_type == 'sd':
                drives = lsdrives(drive)
                current_dir = None
                for i in drives:
                    if i['name'] == to_traverse[-1]:
                        current_dir = i['id']
                        break
                if current_dir == None:
                    print('drive not found: ' + to_traverse[-1])
                    return None
                to_traverse.pop()

            elif path_type == 'fi':
                current_dir = apicall(drive.files().get(
                    fileId=to_traverse.pop()))['id']

            else:
                alias_path = self.config['path_aliases'][path_type]

                if alias_path[0] == 'local':
                    return Path(alias_path[1])
                else:
                    current_dir = apicall(
                        drive.files().get(fileId=alias_path[1]))['id']

            if len(to_traverse) != 1 or len(to_traverse[0]) != 0:
                while len(to_traverse) != 0:
                    search_for = to_traverse.pop()
                    found = False
                    for i in ls(drive, current_dir):
                        if i['name'] == search_for:
                            current_dir = i['id']
                            found = True
                            break
                    if not found:
                        print(f"couldn't find {search_for}!")
                        return None

            return current_dir

        else:
            print(f"unrecognized path type '{path_type}'")

    def log(self, message):

        if not self.silent:

            print(message)

    def confirm(self, message, cancel_key):

        if self.force:
            return True

        yn = input(message)
        if len(yn) > 0 and yn.lower()[0] == cancel_key:
            return False
        else:
            return True

    def overwrite_config(self):

        (self.config_path/'config.json').write_text(json.dumps(_default_config))

    def auth_get(self, name):

        if name in self.authstore:
            return self.authstore['name']

        else:
            to_auth = None
            for i in self.config['accounts']:
                if i['name'] == name:
                    to_auth = i
                    break
            else:
                self.log(f"ERR couldn't find account {name}")
                return None

            auth_dict = json.loads(i['auth'])
            if i['type'] == 'sa':
                creds = service_account.Credentials.from_service_account_info(
                    auth_dict, scopes=_default_scopes)
                self.authstore[i['name']] = creds
                return creds

            elif i['type'] == 'user':
                creds = Credentials.from_authorized_user_info(
                    auth_dict, scopes=_default_scopes)
                creds.refresh(Request())
                i['token'] = creds.token
                self.save_config()
                self.authstore[i['name']] = creds
                return creds

            else:
                self.log(f"WARN unknown auth type '{i['type']}'")
                self.config.remove(to_auth)
                self.save_config()
                return None

    def auth_add_user(self, name, creds_file, remote=False):

        with Path(creds_file).open('r') as f:
            creds_dict = json.load(f)

        flow = InstalledAppFlow.from_client_config(
            creds_dict, scopes=_default_scopes)
        if remote:
            creds = flow.run_console()
        else:
            creds = flow.run_local_server()

        self.authstore[name] = creds
        self.config['accounts'].append({
            'name': name,
            'type': 'user',
            'auth': creds.to_json().replace(' ', '')
        })
        self.save_config()
        return creds

    def auth_add_sa(self, name, creds_file):

        with Path(creds_file).open('r') as f:
            creds_dict = json.load(f)

        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=_default_scopes)
        authstore[name] = creds
        self.config['accounts'].append({
            'name': name,
            'type': 'sa',
            'auth': creds_dict
        })
        self.save_config()
        return creds

    def auth_list_accounts(self):

        return [{
            'name': i['name'],
            'type': i['type']
        } for i in self.config['accounts']]

    def auth_remove_account(self, name):

        for i in self.config['accounts']:
            if i['name'] == name:
                self.config['accounts'].remove(i)
                self.save_config()
                break
        else:
            self.log(f"ERR couldn't find account '{name}'")

        for i in self.authstore:
            if self.authstore[i]['name'] == name:
                del self.authstore[i]
                break

    def alias_add(self, name, path, creds):

        alias_path = self.get_path(path, creds)
        if alias_path == None:
            return None
        elif isinstance(alias_path, Path):
            self.config['path_aliases'][name] = [
                'local', alias_path.as_posix()]
        else:
            self.config['path_aliases'][name] = ['drive', alias_path]

        self.save_config()

    def alias_remove(self, name):

        if name in self.config['path_aliases']:
            del self.config['path_aliases'][name]
        else:
            print(f'ERR alias {name} not found')
        self.save_config()

    def alias_list(self):

        aliases = []
        for i in self.config['path_aliases']:
            alias_data = self.config['path_aliases'][i]
            aliases.append({
                'name': i,
                'type': alias_data[0],
                'path': alias_data[1]
            })

        return aliases

    def save_config(self):

        try:
            config_str = json.dumps(self.config)
        except TypeError as e:
            print(f'ERR failed saving config! reason: {str(e)}')
        (self.config_path/'config.json').write_text(config_str)

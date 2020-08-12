from gdrove.common import apicall, determine_folder, process_recursively
from gdrove.helpers import get_files, lsfolders
from google.oauth2.credentials import Credentials
import progressbar
import aiohttp
import asyncio


class GDException(Exception):

    def __init__(self, data: dict, resp: aiohttp.ClientResponse):

        super(GDException, self).__init__()
        self.reason = data['error']['errors'][0]['reason']
        self.url = resp.url

    def __str__(self) -> str:

        return f'{self.reason} error while requesting {self.url}'

async def copy_file(creds: Credentials, source_file: str, target_folder: str):

    auth_headers = {}
    creds.apply(auth_headers)
    async with aiohttp.ClientSession(headers=auth_headers) as session:
        for i in range(5):
            await asyncio.sleep(2**i)
            async with session.post(f'https://www.googleapis.com/drive/v3/files/{source_file}/copy', params={
                'supportsAllDrives': 'true'
            }, json={
                'parents': [target_folder]
            }) as response:
                data = await response.json()

                if response.status >= 400:
                    retryable = False

                    if response.status == 403: # could be retryable
                        if data['error']['errors'][0]['reason'] == 'userRateLimitExceeded':
                            retryable = True

                    if response.status == 429: # ratelimit
                        retryable = True

                    if response.status >= 500: # internal error
                        retryable = True

                    if retryable:
                        continue
                    else:
                        raise GDException(data, response)

                else:
                    return data


def compare_function(drive, source_file, dest_file, dest_dir):
    if source_file['name'] == dest_file['name']:
        if source_file['md5'] == dest_file['md5']:
            return True, None, None
        return True, (source_file['id'], dest_dir), dest_file
    return False, None, None


def new_folder_function(drive, folder_name, folder_parent):

    return apicall(drive.files().create(body={
        'mimeType': 'application/vnd.google-apps.folder',
        'name': folder_name,
        'parents': [folder_parent]
    }, supportsAllDrives=True))['id']


def sync(drive, sourceid, destid):

    copy_jobs, delete_jobs = process_recursively(
        drive, sourceid, destid, compare_function, new_folder_function)

    if len(copy_jobs) > 0:
        for i in progressbar.progressbar(copy_jobs, widgets=['copying files ', progressbar.Counter(), '/' + str(len(copy_jobs)), ' ', progressbar.Bar(), ' ', progressbar.AdaptiveETA()]):
            apicall(drive.files().copy(fileId=i[0], body={
                    'parents': [i[1]]}, supportsAllDrives=True))
    else:
        print('nothing to copy')

    if len(delete_jobs) > 0:
        for i in progressbar.progressbar(delete_jobs, widgets=['deleting files ', progressbar.Counter(), '/' + str(len(delete_jobs)), ' ', progressbar.Bar(), ' ', progressbar.AdaptiveETA()]):
            apicall(drive.files().delete(fileId=i, supportsAllDrives=True))
    else:
        print('nothing to delete')

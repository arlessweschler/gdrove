from gdrove.common import determine_folder, process_recursively
from gdrove.helpers import apicall, get_files, lsfolders, get_drive
from google.oauth2.credentials import Credentials
import progressbar
import aiohttp
import asyncio


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
        i = -1
        while True:
            i += 1
            await asyncio.sleep(min(i, 6)) # exponential backoff is for losers who aren't queueing up 1000s of requests
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


async def prune_completed(tasks):

    i = 0
    while i < len(tasks):
        if not tasks[i].cr_running:
            await tasks[i]
            del tasks[i]
        else:
            i += 1

async def async_copy(creds, copy_jobs):

    copy_tasks = []
    i = 0
    with progressbar.ProgressBar(max_value=len(copy_jobs), widgets=['copying files ', progressbar.Counter(), '/' + str(len(copy_jobs)), ' ', progressbar.Bar(), ' ', progressbar.AdaptiveETA()]) as pbar:
        while len(copy_jobs) > 0 or len(copy_tasks) > 0:
            while len(copy_tasks) > 10:
                await prune_completed(copy_tasks)
                await asyncio.sleep(0.1)
            if len(copy_jobs) == 0:
                while len(copy_tasks) > 0:
                    await prune_completed(copy_tasks)
                    await asyncio.sleep(0.1)
                break
            new_copy = copy_jobs.pop()
            copy_tasks.append(copy_file(creds, new_copy[0], new_copy[1]))
            i += 1
            pbar.update(i)

def sync(creds, sourceid, destid):

    drive = get_drive(creds)

    copy_jobs, delete_jobs = process_recursively(
        drive, sourceid, destid, compare_function, new_folder_function)

    if len(copy_jobs) > 0:
        asyncio.run(async_copy(creds, copy_jobs))
    else:
        print('nothing to copy')

    if len(delete_jobs) > 0:
        for i in progressbar.progressbar(delete_jobs, widgets=['deleting files ', progressbar.Counter(), '/' + str(len(delete_jobs)), ' ', progressbar.Bar(), ' ', progressbar.AdaptiveETA()]):
            apicall(drive.files().delete(fileId=i, supportsAllDrives=True))
    else:
        print('nothing to delete')

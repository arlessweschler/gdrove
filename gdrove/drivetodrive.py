from gdrove.helpers import get_files, lsfolders, apicall
import progressbar

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

        to_copy, to_delete = sync_directory(drive, currently_processing[0], currently_processing[1])
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

def sync_directory(drive, sourceid, destid):

    source_files = get_files(drive, sourceid)
    dest_files = get_files(drive, destid)

    # sets because we don't want to try to delete or copy the same file twice
    to_copy = set()
    to_delete = set()

    to_process_length = len(source_files) + len(dest_files)
    count = 0
    with progressbar.ProgressBar(0, to_process_length, ["processing files ", progressbar.Counter(), "/" + str(to_process_length), " ", progressbar.Bar()]).start() as pbar:
        for source_file in source_files: # check for new files and new file versions
            for dest_file in dest_files:
                if source_file["name"] == dest_file["name"]: #      if the files have the same name
                    if source_file["md5"] == dest_file["md5"]: #        and the same md5
                        break #                                         then the file hasn't changed
                    else: #                                         else
                        to_copy.add(source_file["id"]) #             copy over new version of file
                        to_delete.add(dest_file["id"]) #             and delete old version of file
            else: #                                 if the source file isn't found in the destination
                to_copy.add(source_file["id"]) #     then it must be a new file, so it will be copied
            count += 1
            pbar.update(count)
        
        for dest_file in dest_files: # check for deleted files
            if dest_file["id"] in to_delete: #  if we're already deleting the file
                continue #                          ignore it
            for source_file in source_files:
                if source_file["name"] == dest_file["name"]: #  if files have the same name
                    break #                                      don't delete it
            else: #                                 if no match in source files
                to_delete.add(dest_file["id"]) #     delete the file
            count += 1
            pbar.update(count)
    
    return to_copy, to_delete
from pathlib import Path
from gdrove.helpers import lsfolders, item_name, item_id, list_path, apicall
import progressbar


def process_recursively(drive, source_dir, dest_dir, compare_function, new_folder_function):

    from_local = isinstance(source_dir, Path)
    to_local = isinstance(dest_dir, Path)

    to_process = set()
    to_process.add((source_dir, dest_dir))

    create_jobs = set()
    delete_jobs = set()

    while len(to_process) > 0:

        print(f'{len(to_process)} folders is queue')

        currently_processing = to_process.pop()

        if from_local:
            source_folders = [
                i for i in currently_processing[0].iterdir() if i.is_dir()]
        else:
            source_folders = lsfolders(drive, currently_processing[0])

        if to_local:
            dest_folders = [
                i for i in currently_processing[1].iterdir() if i.is_dir()]
        else:
            dest_folders = lsfolders(drive, currently_processing[1])

        folders_to_delete = set()

        for source_folder in source_folders:
            source_folder_name = item_name(source_folder)
            for dest_folder in dest_folders:
                if source_folder_name == item_name(dest_folder):
                    to_process.add(
                        (item_id(source_folder), item_id(dest_folder)))
                    break
            else:
                print(
                    f'creating new directory \'{item_name(source_folder)}\' in {currently_processing[1]}')
                to_process.add((item_id(source_folder), new_folder_function(
                    drive, item_name(source_folder), currently_processing[1])))

        for dest_folder in dest_folders:
            dest_folder_name = item_name(dest_folder)
            for source_folder in source_folders:
                if item_name(source_folder) == dest_folder_name:
                    break
            else:
                folders_to_delete.add(item_id(dest_folder))

        to_create, to_delete = determine_folder(
            drive, currently_processing[0], currently_processing[1], compare_function)
        to_delete.update(folders_to_delete)

        create_jobs.update(to_create)
        delete_jobs.update(to_delete)

    return create_jobs, delete_jobs


def determine_folder(drive, source_dir, dest_dir, compare_function):

    source_files = list_path(drive, source_dir)
    dest_files = list_path(drive, dest_dir)

    from_local = isinstance(source_dir, Path)
    to_local = isinstance(dest_dir, Path)

    if from_local:
        source_filename = source_dir.name
    else:
        source_filename = apicall(drive.files().get(fileId=source_dir))['name']

    to_create = set()
    to_delete = set()

    to_process_length = len(source_files) + len(dest_files)
    count = 0
    with progressbar.ProgressBar(0, to_process_length, ['processing files (' + source_filename + ') ', progressbar.Counter(), '/' + str(to_process_length), ' ', progressbar.Bar()]).start() as pbar:
        for source_file in source_files:
            for dest_file in dest_files:
                match_found, add_item, delete_item = compare_function(
                    drive, source_file, dest_file, dest_dir)
                if match_found:
                    if add_item:
                        to_create.add(add_item)
                    if delete_item:
                        to_delete.add(delete_item)
                    break
            else:
                if from_local:
                    to_create.add((source_file, dest_dir))
                elif to_local:  # hacky solution, i know
                    to_create.add(
                        (source_file['id'], dest_dir, source_file['name'], source_file['size']))
                else:
                    to_create.add((source_file['id'], dest_dir))
            count += 1
            pbar.update(count)

        for dest_file in dest_files:
            if to_local:
                if dest_file in to_delete:
                    continue
            else:
                if dest_file['id'] in to_delete:
                    continue

            for source_file in source_files:
                if from_local:
                    source_filename = source_file.name
                else:
                    source_filename = source_file['name']
                if to_local:
                    dest_filename = dest_file.name
                else:
                    dest_filename = dest_file['name']

                if source_filename == dest_filename:
                    break
            else:
                if to_local:
                    to_delete.add(dest_file)
                else:
                    to_delete.add(dest_file['id'])
            count += 1
            pbar.update(count)

    return to_create, to_delete

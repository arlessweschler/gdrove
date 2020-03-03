from gdrove.helpers import get_files
import progressbar

def sync(drive, sourceid, destid):

    source_files = get_files(drive, sourceid)
    dest_files = get_files(drive, destid)

    # sets because we don't want to try to delete or copy the same file twice
    to_copy = {}
    to_delete = {}

    to_process_length = len(source_files) + len(dest_files)
    with progressbar.ProgressBar(0, to_process_length, ["processing files ", progressbar.Counter(), "/" + str(to_process_length), " ", progressbar.Bar()]) as pbar:
        for source_file in source_files: # check for new files and new file versions
            for dest_file in dest_files:
                if source_file["name"] == dest_file["name"]: #      if the files have the same name
                    if source_file["md5"] == dest_file["md5"]: #        and the same md5
                        break #                                         then the file hasn't changed
                    else: #                                         else
                        to_copy.append(source_file["id"]) #             copy over new version of file
                        to_delete.append(dest_file["id"]) #             and delete old version of file
            else: #                                 if the source file isn't found in the destination
                to_copy.append(source_file["id"]) #     then it must be a new file, so it will be copied
            pbar.next()
        
        for dest_file in dest_files: # check for deleted files
            if dest_file["id"] in to_delete: #  if we're already deleting the file
                continue #                          ignore it
            for source_file in source_files:
                if source_file["name"] == dest_file["name"]: #  if files have the same name
                    continue #                                      don't delete it
            else: #                                 if no match in source files
                to_delete.append(dest_file["id"]) #     delete the file
            pbar.next()
    
    # make actually copy later
    print(to_copy)
    print(to_delete)
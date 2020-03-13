# gdrove
An RClone-like Google Drive tool to help you sync files to and from your personal computer and between Google Drive folders!

# install
#### windows
`pip install gdrove`
#### linux
`pip3 install gdrove`

# paths
Paths can be of five types: local (ld), my drive (md), shared drive (sd), file id (fi), and alias.
#### format
Paths are formatted as `path_type:dir1/dir2/dir3`, where `path_type` is the type of path (see below) and `dir1/dir2/dir3` is the path to the file from wherever you want.
#### local (ld)
Local, specified as `ld:path/to/some/folder`, represent a local directory to download to or upload from.
#### my drive (md)
My Drive, specified as `md:path/to/some/folder`, is similar to RClone's method of paths, where the path is revative to your my drive folder.
#### shared drive (sd)
Shared Drive, specified as `sd:drive_name/some/directory`, where `drive_name` is the name of a Shared Drive, reference a file in a Shared Drive, whose name you specify as the first directory.
#### file id (fi)
File Id, specified as `fi:S0M3_F1L3_1D`, where `S0M3_F1L3_1D` is a File Id accessable to your user. This is the biggest thing RClone doesn't have, and allows you to clone from random public directories without having to add them to My Drive.
#### alias
Alias, specified as `alias_name:path/to/some/folder`, uses an alias to show some root folder. This feature is still being worked on and will be fleshed out later.

# auth
To authenticate with gdrove, you'll need to create a `credentials.json` in the directory you're running the program in. This requirement may be lifted in the future, with default credentials supplied. You can use `gdrove config account user acnt_name` to create and authorize a new account named `acnt_name`. You can also create a Serivce Account using `gdrove config account sa acnt_name sa.json` to create a new Serivce Account named `acnt_name` using the Service Account file `sa.json`.

# syncing
To sync, use `gdrove sync account_name source_path destination_path`, with `account_name` being the name of an account, `source_path` being the path to the source folder, and `destination_path` being the path to the destination folder.

# TODO
- Refactor, putting filtering logic in it's own function with a callback/comparison function
- Implement multithreaded dtd
- Measure performance benefits of multithreaded ltd and dtl on high bandwidth machines
- Implement impersonation (not as bad as it sounds, I swear)

# Maybe TODO
- Implement dtltd (download from drive to local then reupload to other account, for when you want to copy between accounts when only one account has access to each side)

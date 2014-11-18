import os, hashlib, shutil, textwrap, re
from crypto.file import EncryptedFile, PlainFile, getLocalFileMod, FileMeta
from actions import DeleteRemoteFromMetaAction, DeleteLocalAction, UploadAction, DownloadAction

__author__ = 'pezza'






class Synchronizer:
    def __init__(self, root_path):
        self.root_path = root_path

    def getLocalFiles(self):
        local_files = []
        for root, dirs, files in os.walk(self.root_path):
            for f in files:
                m = re.search(".*(\.conflictedcopy)(\.*)(\d*)$", f)
                if m is None:
                    full_path = os.path.join(root, f)
                    local_files.append(os.path.relpath(full_path, self.root_path))

        return local_files

    def makeConflictedCopy(self, path):
        m = re.search(".*(\.conflictedcopy)(\.*)(\d*)$", path)
        extension = "conflictedcopy"
        if m is not None:
            num = "1"
            elems = m.groups()
            if len(elems) > 1:
                num = int(elems[2])

            extension = "%s.%s" % (extension, str(num))

        newpath = "%s.%s" % (path, extension)

        os.rename(os.path.join(self.root_path, path), os.path.join(self.root_path, newpath))

        return newpath

    def handleLocalChanges(self, local_index, crypt):
        actions = []
        files = set(self.getLocalFiles())
        indexed = set(local_index.getFiles())

        # for all the files on the filesystem which are indexed
        for path in (files & indexed):
            fileMod = getLocalFileMod(os.path.join(self.root_path, path))
            indexMod = local_index.getLocalFileMod(path)

            if fileMod > indexMod:
                # upload the file
                actions.append(UploadAction(PlainFile, None, local_index.getFileMeta(path).asUrl(), path, crypt, self.root_path))
                print "File %s has been updated locally --> upload" % path

        # for all the files on the filesystem that are not in the index
        for path in (files - indexed):
            actions.append(UploadAction(PlainFile, None, None, path, crypt, self.root_path))
            print "File %s has been added locally --> upload" % path

        # for all the files in the index that are not on the filesystem
        for path in (indexed - files):
            log = local_index.getTransaction(path)

            if log is not None and log[0] == 'add':
                # Remove file from the repository
                actions.append(DeleteRemoteFromMetaAction(local_index.getFileMeta(path), path))
                #actions.append(DeleteLocalAction(self.root_path, path))
                print "File %s has been removed locally, is not on the filesystem but is in the local index --> delete remote and from local index" % path
            else:
                # file has been removed locally, but outside of our logic.
                # check and download again
                actions.append(DownloadAction(EncryptedFile, None, remote_index.getFileMeta(path).getMeta(), crypt, self.root_path))
                print "File %s has been removed locally in a unusual way --> download" % path

        return actions

    def removePaths(self, paths, index, crypt):
        actions = []
        for remote_path, meta in paths.items():
            #remotekey, remotesalt, path, remotemod = meta.decryptMeta(crypt.keys[0])
            remotekey, remotesalt, path, remotemod = crypt.decryptMeta(meta)
            indexMeta = index.getFileMeta(path)

            if indexMeta is not None:
                action = self.removeByMeta(indexMeta, meta, crypt)
                if action is not None:
                    actions.append(self.removeByMeta(indexMeta, meta, crypt))
            else:
                print "File %s has been removed remotely, but it's not on our filesystem --> no action" % path

        return actions

    def removeByMeta(self, local_meta, remote_meta, crypt):
        #localkey, localsalt, path, localmod = local_meta.decryptMeta(crypt.keys[0])
        localkey, localsalt, path, localmod = crypt.decryptMeta(local_meta)
        action = None

        if local_meta.getMeta() == remote_meta.getMeta():
            # the returned path is in the index, let's remove it
            action = DeleteLocalAction(self.root_path, path)
            print "File %s has been removed remotely --> remove locally" % path
        else:
            # the file has been deleted remotely, but our copy has a different meta
            # let's check them
            #localkey, localsalt, localpath, localmod = local_meta.decryptMeta(crypt.keys[0])
            localkey, localsalt, localpath, localmod = crypt.decryptMeta(local_meta)
            #remotekey, remotesalt, remotepath, remotemod = remote_meta.decryptMeta(crypt.keys[0])
            remotekey, remotesalt, remotepath, remotemod = crypt.decryptMeta(remote_meta)

            if localmod > remotemod:
                # Our local copy is better than the remote copy
                print "File %s has been removed remotely, but our copy is better --> no action" % (path)
            else:
                # Our local copy is even same or worse than the remote copy
                action = DeleteLocalAction(self.root_path, path)
                print "File %s has been removed remotely, and our copy is same or older --> remove locally" % path
        
        return action

    def handleRemoteChanges(self, modified, index, crypt):
        actions = []
        for remote_path, meta in modified.items():
            path = meta.getFilePath()
            indexMeta = index.getFileMeta(remote_path)
            #remotekey, remotesalt, remotepath, remotemod = meta.decryptMeta(crypt.keys[0])
            remotekey, remotesalt, remotepath, remotemod = crypt.decryptMeta(meta)

            if indexMeta is None:
                # file has been added remotely, and it's not in our index.
                if os.path.isfile(os.path.join(self.root_path, remotepath)):
                    # We'd like to download, but a file with the same name is already on the filesystem.
                    # Rename this one as "*.conflictedcopy" and proceed with download
                    conflictedPath = self.makeConflictedCopy(remotepath)

                    # remove file from the index, so that it'll be added again by the download action.
                    # this is necessary to ensure that, if the download fails, we'll not assume that the file (still in the index but
                    # not on the filesystem anymore) has been deleted and remove it remotely
                    index.removeFile(remotepath)
                    print "File %s needs to be downloaded but it exists on the filesystem, and is not in the index. It has been renamed to %s." % (remotepath, conflictedPath)

                actions.append( DownloadAction(EncryptedFile, None, meta.getMeta(), crypt, self.root_path))
                print "File %s has been created remotely --> download" % remotepath
            else:
                print "Decrypting %s" % remote_path
                #localkey, localsalt, localpath, localmod = indexMeta.decryptMeta(crypt.keys[0])
                localkey, localsalt, localpath, localmod = crypt.decryptMeta(indexMeta)
 
                if remotemod > localmod:
                    # file has been updated remotely, download it and replace in our index
                    actions.append( DownloadAction(EncryptedFile, None, meta.getMeta(), crypt, self.root_path))
                    print "File %s has been updated remotely --> download" % remotepath
                elif localmod > remotemod:
                    # file has been updated remotely, but our copy is better
                    actions.append( UploadAction(PlainFile, None, meta.asUrl(), localpath, crypt, self.root_path))
                    print "File %s has been removed remotely, but our copy is better --> upload" % remotepath
                else:
                    print "File %s has been updated remotely, but our version has same timestamp --> no action" % localpath

        return actions

    def spin(self, modified, removed, local_index, crypt):
        actions = self.removePaths(removed, local_index, crypt)
        actions.extend(self.handleRemoteChanges(modified, local_index, crypt))

        return actions



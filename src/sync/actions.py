import os, traceback, textwrap, shutil
from settings import APP_PATH
from dropbox.rest import ErrorResponse
from repo.dropbox.wrapper import DropboxWrapper
from cStringIO import StringIO
from crypto.file import FileMeta
from crypto.exceptions import AuthenticationException


__author__ = 'pezza'




class ActionFailedException(Exception):
    pass

class FileAction(DropboxWrapper):
    def __init__(self, cl, *args, **kwargs):
        self.action = cl
        self.args = args
        self.kwargs = kwargs
        self.fileObj = None
        self.metas = []

    def execute(self):
        self.setup()

    def setup(self):
        self.fileObj = self.action(*self.args, **self.kwargs)

    def getMetas(self):
        return self.metas

    def removeLocal(self, file):
        try:
            os.unlink(file)
            print "Removed %s" % file

            rootFolder = os.path.dirname(file)
            if rootFolder != APP_PATH:
                files = os.listdir(rootFolder)
                if len(files) == 0:
                    os.rmdir(rootFolder)
                    print "Removed empty folder %s" % rootFolder

        except Exception, e:
            print "Cannot remove %s:%s" % ( file, e )
            #print traceback.format_exc()

class DeleteAction(FileAction):
    def __init__(self, meta):
        FileAction.__init__(self, None)
        self.metas.append(meta)

    def setup(self):
        pass

    def execute(self, client, local_index):
        pass

class DeleteRemoteFromMetaAction(DeleteAction):
    def __init__(self, meta, path):
        DeleteAction.__init__(self, meta)
        self.path = path
    def execute(self, client, local_index):
        FileAction.execute(self)

        print "Deleting %s remotely" % self.path
        # get the remote "view" on this local path
        try:
            self.removeRemote(self.metas[0].asUrl(), client)
            local_index.removeFile(self.path)
            print "* index updated"
        except ErrorResponse, er:
            status = er.status

            # if the remote file is gone already, remove it from the index
            if status == 404:
                local_index.removeFile(self.path)
                print "* file has been removed already, updated index"

class DeleteLocalAction(DeleteAction):
    def __init__(self, root, path):
        self.file = os.path.join(root, path)
        self.path = path
        self.metas = []

    def execute(self, client, local_index):
        FileAction.execute(self)

        print "Deleting %s (complete path is %s)" % (self.path, self.file)
        self.removeLocal(self.file)
        self.metas.append( local_index.getFileMeta(self.path) )
        local_index.removeFile(self.path)
        print "* index updated"

class UploadAction(FileAction):
    def __init__(self, cl, remotePath, currentRemotePath, *args, **kwargs):
        FileAction.__init__(self, cl, *args, **kwargs)
        self.remotePath = remotePath
        self.currentRemotePath = currentRemotePath

    def execute(self, client, local_index):
        FileAction.execute(self)
        self.metas.append(self.fileObj.getFileMeta())
        
        fileLength = os.path.getsize(self.fileObj.getFileFullPath())

        print "Uploading %s" % self.fileObj.getFilePath()

        # upoad in one go if the file is small
        if fileLength < 8192:
            print "* using single chunk method"
            self.checkCurrentRemotePath(client, local_index)
            self.upload(client, self.remotePath)
        else:
            # If the file has been removed, this will cause a deadlock,
            # since actions cannot fail.
            # TODO Investigate ways to lock the file before adding the action
            print "* using streaming method"
            uploader = self.uploadChunks(client)
            self.checkCurrentRemotePath(client, local_index)
            print "* upload complete, moving to final destination"
            self.finalizeUpload(uploader, self.remotePath)

        # update index
        local_index.addFile(self.fileObj.getFilePath(), self.fileObj.getFileMeta().getMeta())
        print "* index updated"

    def checkCurrentRemotePath(self, client, local_index):
        # Remove the remotely stored version before uploading a new one
        # Note that the fileMeta stored in the fileObj is *not* the
        # one used remotely, due to encryption/salting
        # In other words, if you don't remove the "old" version before uploading a new one
        # you'll end up with 2 encrypted version of the same file!
        if self.currentRemotePath is not None:
            print "* removing remote copy before uploading a more recent version"
            try:
                self.removeRemote(self.currentRemotePath, client)
                local_index.removeFile(self.fileObj.getFilePath())
                oldMeta = "".join(self.currentRemotePath.split('/'))

                # return the additional meta, so that we'll keep it into account
                # when handling changes next time
                self.metas.append(FileMeta(oldMeta.encode("utf8")))
            except ErrorResponse, er:
                status = er.status

                # generic error
                if status == 400 or status == 406:
                    print traceback.format_exc()
                # not found
                elif status == 404:
                    local_index.removeFile(self.fileObj.getFilePath())
                    print "* remote copy has been deleted already, updating local index"
                else:
                    print traceback.format_exc()

class DownloadAction(FileAction):
    def __init__(self, cl, remotePath, *args, **kwargs):
        FileAction.__init__(self, cl, *args, **kwargs)
        self.remotePath = remotePath

    def execute(self, client, local_index):
        FileAction.execute(self)
        self.meta = self.fileObj.getFileMeta()

        print "Downloading %s" % self.fileObj.getFilePath()
        f = self.fileObj.getFileFullPath()
        if os.path.isfile(f):
            self.removeLocal(f)
            local_index.removeFile(self.fileObj.getFilePath())
            print "* removed old copy"

        try:
            self.download(client, self.fileObj.getFilePath(), self.remotePath )
            print "* download complete"

            # update indexes
            local_index.addFile(self.fileObj.getFilePath(), self.fileObj.getFileMeta().getMeta())
            print "* index updated"

        except ErrorResponse, er:
            status = er.status
            if status == 404:
                pass
            else:
                raise er

        except AuthenticationException, e:
            # remove any file fragment
            self.removeLocal(self.fileObj.getFileFullPath())

            # remove file from index
            local_index.removeFile(self.fileObj.getFilePath())

            print "* WARNING: failed authentication, file invalid. Removed from filesystem"


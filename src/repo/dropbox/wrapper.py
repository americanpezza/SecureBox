import os, traceback, cStringIO
from crypto.exceptions import EndOfFileException

__author__ = 'pezza'





class DropboxWrapper:
    def __init__(self, fileObj=None):
        self.fileObj = fileObj

    def download(self, client, path, remotePath=None):
        
        if remotePath is None:
            meta = self.fileObj.getFileMeta()
            remotePath = meta.asUrl()

        f, meta = client.get_file_and_metadata(remotePath)

        # run the show!
        self.fileObj.decrypt(f)

        f.close()
        self.fileObj.close()

    def upload(self, client, remotePath=None):
        if remotePath is None:
            meta = self.fileObj.getFileMeta()
            remotePath = meta.asUrl()

        # TODO: handle exceptions
        metadatata = client.put_file(remotePath, self.fileObj, overwrite=True ) 

        self.fileObj.close()

    def uploadChunks(self, client):

        plainFileLength = os.path.getsize(self.fileObj.getFileFullPath())
        uploader = client.get_chunked_uploader(self.fileObj, int(plainFileLength * 100))

        # TODO: handle other exceptions
        try:
            uploader.upload_chunked()
        except EndOfFileException, e:
            pass

        return uploader

    def finalizeUpload(self, uploader, remotePath=None):
        if remotePath is None:
            meta = self.fileObj.getFileMeta()
            remotePath = meta.asUrl()

        # TODO: check this error condition, might lead to a weird situation if there's
        #       a REST error and the file is not uploaded
        uploader.finish(remotePath, overwrite=True)

        self.fileObj.close()

    def removeRemotePath(self, path, client):
        client.file_delete(path)
        
    def removeRemote(self, path, client):
        # remove all intermediate folders and the final file
        # in reverse order
        parts = path.split('/')
        to_remove = []
        current = ''
        for part in parts:
            current = current + part + '/'
            to_remove.insert(0, current)

        # don't try to remove the root folder!
        to_remove.pop()

        for path in to_remove:
            client.file_delete(path)


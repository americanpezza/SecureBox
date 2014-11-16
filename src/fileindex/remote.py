import os, shutil
from crypto.file import FileMeta, EmbeddedEncryptedFile, EmbeddedPlainFile
from base import FileIndex
import repo.dropbox.wrapper as wrapper
import tempfile

__author__ = 'pezza'





class RemoteIndex(FileIndex, wrapper.DropboxWrapper):
    def __init__(self, path, index):
        FileIndex.__init__(self, path, index)
        self.fileObj = None

    def addFile(self, path, meta):
        self.addRecord(path, meta)

    def removeFile(self, path):
        self.removeRecord(path)

    def getFileMeta(self, path):
        result = self.getRecord(path)
        if result is not None:
            result = FileMeta(result[0])
        
        return result

    def download(self, client, crypt):
        response = None
        self.fileObj = EmbeddedEncryptedFile(crypt, self.index_path, self.index_file)
        response = wrapper.DropboxWrapper.download(self, client, self.index_file, "/" + self.index_file)
        self.fileObj.close()
        self.fileObj = None

        return response

    def upload(self, client, crypt):
        response = None
        self.fileObj = EmbeddedPlainFile(self.index_file, crypt, self.index_path)
        uploader = wrapper.DropboxWrapper.uploadChunks(self, client)
        
        wrapper.DropboxWrapper.finalizeUpload(self, uploader, "/" + self.index_file)

        self.fileObj.close()
        self.fileObj = None

    def getLocalPath(self, meta):
        result = None
        for key in self.getFiles():
            data = self.getRecord(key)[0]
            if data == meta:
                result = key

        return result

    def verify(self, client):
        result = None

        tmpFolder = ""
        fileName = ""
        try:
            # create a temporary location for the remote index to download to
            tmpFolder = tempfile.mkdtemp()
            indexFile = self.getIndexFilePath()
            fileName = os.path.relpath(indexFile, self.remoteIndex.getIndexPath())
            
            tempIndex = RemoteIndex(tmpFolder, indexFile)

            
        finally:
            if fileName != "":
                os.unlink(fileName)

            if tmpFolder != "":
                shutil.rmtree(folder)

        return result

 





def test():
    from subprocess import call
    import os

    indexFile = "remoteindex.local"
    indexPath = "/tmp/"

    test1 = "/test.local"
    test2 = "/test2.local"
    
    metaIndex = RemoteIndex(indexPath, indexFile)

    metaIndex.addFile(test1, "NGXVAKA4QMTRCH5XFYZI5GE4266SWIY7752OASAFGNMNLU5A5O4BCFS55YNIVXAPCGRFDDZ3SODYUOEXJIXQYMO4CFEJSHVN2QMBZQGXZX5UMN5IDWMF3CDVVDYQBKSK$HGTESCAI7CVYRPWGOXD5QIOR54======$2CBKDFW5KQJYNBZKHTXPAPIF6FPMM4M6BUQA7EEYOON4EGUTN5SA====$P56IOIO5MOXUZ7MTOYEHJELEL3AYXI2Z3WNOB3M6HDAPVWARREPLG7KKVXDHHGOYJ4YME54KWL75PUZJ6DEJH2PEBT5DVOU2RRGWD3I=$QTEN7IO6IAADG2OH5Z7ZUIVBZOENPF62JK26XAUWWX6VYW32CAIKXVCVAO3ATCZBEJSQ64SKLLYOAXLOBFZUWP2IIIALCMFPH3OX3LA=")
    metaIndex.addFile(test2, "NGXVAKA4QMTRCH5XFYZI5GE4266SWIY7752OASAFGNMNLU5A5O4BCFS55YNIVXAPCGRFDDZ3SODYUOEXJIXQYMO4CFEJSHVN2QMBZQGXZX5UMN5IDWMF3CDVVDYQBKSK$HGTESCAI7CVYRPWGOXD5QIOR54======$2CBKDFW5KQJYNBZKHTXPAPIF6FPMM4M6BUQA7EEYOON4EGUTN5SA====$P56IOIO5MOXUZ7MTOYEHJELEL3AYXI2Z3WNOB3M6HDAPVWARREPLG7KKVXDHHGOYJ4YME54KWL75PUZJ6DEJH2PEBT5DVOU2RRGWD3I=$QTEN7IO6IAADG2OH5Z7ZUIVBZOENPF62JK26XAUWWX6VYW32CAIKXVCVAO3ATCZBEJSQ64SKLLYOAXLOBFZUWP2IIIALCMFPH3OX3LA=")
    
    print "test.local is  %s" % str(metaIndex.getFileMeta(test1))

    metaIndex.removeFile(test1)

    assert metaIndex.getFileMeta(test1) is None

    print "Transaction log for index is:\n%s" % str(metaIndex.getTransactions())

    metaIndex.save()

    metaIndex.clear()
    assert metaIndex.getFileMeta(test2) is None

    metaIndex.load()
    assert metaIndex.getFileMeta(test2) is not None

    print "Transaction log for index after save/clear/load is:\n%s" % str(metaIndex.getTransactions())

    assert metaIndex.getTransaction(test2) is not None
    metaIndex.removeTransaction(test2)
    assert metaIndex.getTransaction(test2) is None

    print "Transaction log for index after save/clear/load is:\n%s" % str(metaIndex.getTransactions())


    call(["rm", os.path.join(indexPath, indexFile)])

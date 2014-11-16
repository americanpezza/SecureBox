import os
from crypto.file import FileMeta, getLocalFileMod
from base import FileIndex
__author__ = 'pezza'



class InvalidFileException(Exception):
    pass



class LocalIndex(FileIndex):
    def __init__(self, path, index, fileRoot):
        FileIndex.__init__(self, path, index)
        self.fileRoot = fileRoot

    def addFile(self, path, fileMeta):
        if path is not None and fileMeta is not None:
            self.addRecord(path, str(getLocalFileMod(os.path.join(self.fileRoot, path))), fileMeta)
        else:
            raise InvalidFileException("File %s has invalid meta, can't update index" % path)

    def getFileMeta(self, path):
        result = self.getRecord(path)
        if result is not None:
            result = FileMeta(result[1])
        
        return result

    def getLocalFileMod(self, path):
        result = self.getRecord(path)
        if result is not None:
            result = float(result[0])

        return result

    def removeFile(self, path):
        self.removeRecord(path)

    def has_metaFragment(self, fragment):
        result = False
        for path in self.getFiles():
            meta = self.getFileMeta(path).getMeta()
            if meta.startswith(fragment):
                result = True
                break

        return result

def test():
    from subprocess import call

    indexFile = "testlocalindex.local"
    indexPath = "/tmp"
   
    test1 = "test.local"
    test2 = "test2.local"
    metaIndex = LocalIndex(indexPath, indexFile, indexPath)

    call(["touch", os.path.join(indexPath, test1), os.path.join(indexPath, test2)])

    metaIndex.addFile(test1, "NGXVAKA4QMTRCH5XFYZI5GE4266SWIY7752OASAFGNMNLU5A5O4BCFS55YNIVXAPCGRFDDZ3SODYUOEXJIXQYMO4CFEJSHVN2QMBZQGXZX5UMN5IDWMF3CDVVDYQBKSK$HGTESCAI7CVYRPWGOXD5QIOR54======$2CBKDFW5KQJYNBZKHTXPAPIF6FPMM4M6BUQA7EEYOON4EGUTN5SA====$P56IOIO5MOXUZ7MTOYEHJELEL3AYXI2Z3WNOB3M6HDAPVWARREPLG7KKVXDHHGOYJ4YME54KWL75PUZJ6DEJH2PEBT5DVOU2RRGWD3I=$QTEN7IO6IAADG2OH5Z7ZUIVBZOENPF62JK26XAUWWX6VYW32CAIKXVCVAO3ATCZBEJSQ64SKLLYOAXLOBFZUWP2IIIALCMFPH3OX3LA=")
    metaIndex.addFile(test2, "NGXVAKA4QMTRCH5XFYZI5GE4266SWIY7752OASAFGNMNLU5A5O4BCFS55YNIVXAPCGRFDDZ3SODYUOEXJIXQYMO4CFEJSHVN2QMBZQGXZX5UMN5IDWMF3CDVVDYQBKSK$HGTESCAI7CVYRPWGOXD5QIOR54======$2CBKDFW5KQJYNBZKHTXPAPIF6FPMM4M6BUQA7EEYOON4EGUTN5SA====$P56IOIO5MOXUZ7MTOYEHJELEL3AYXI2Z3WNOB3M6HDAPVWARREPLG7KKVXDHHGOYJ4YME54KWL75PUZJ6DEJH2PEBT5DVOU2RRGWD3I=$QTEN7IO6IAADG2OH5Z7ZUIVBZOENPF62JK26XAUWWX6VYW32CAIKXVCVAO3ATCZBEJSQ64SKLLYOAXLOBFZUWP2IIIALCMFPH3OX3LA=")

    print "test.local is  %s" % str(metaIndex.getFileMeta("/" + test1))

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

    call(["rm", os.path.join(indexPath, indexFile), os.path.join(indexPath, test1), os.path.join(indexPath, test2)])


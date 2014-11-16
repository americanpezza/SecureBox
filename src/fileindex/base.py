import os, time 
import cPickle
from datetime import datetime
from crypto.file import FileMeta, getLocalFileMod

__author__ = 'pezza'


SEPARATOR = "$$$"




# Return the timestamp in utc seconds
def totimestamp(dt, epoch=datetime(1970,1,1)):
    td = dt - epoch

    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 1e6

def getTimestamp():
    return totimestamp(datetime.utcnow()) 

class KeyValuesStore:
    def __init__(self, index_path, index_file):
        self.indexDataFile = os.path.join(index_path, index_file)
        self.index_file = index_file
        self.index_path = index_path
        self.cursor = 0
        self.dirty = False
        self.records = {}

        # Load index if possible
        if os.path.exists(self.indexDataFile):
            self.load(True)

    def save(self, force=False):
        with open(self.indexDataFile, 'wb') as f:
            self.records['___cursor___'] = self.cursor
            cPickle.dump(self.records, f, 2)
            del self.records['___cursor___']
        
        self.dirty = False

    def load(self, force=False):
        with open(self.indexDataFile, 'r') as f:
            data = cPickle.load(f)

            newCursor = data['___cursor___']
            del data['___cursor___']

            if newCursor is not None and newCursor != '':
               if float(newCursor) < float(self.cursor) and not force:
                   print "WARNING: index is up to date, not loading"
               else:
                    self.cursor = float(newCursor)
                    self.records = data

    def loadRecord(self, parts):
        key = parts.pop(0)
        self.records[key] = parts

    def clear(self):
        self.records = {}
        self.cursor = 0.0

    def isDirty(self):
        return self.dirty

    def makeDirty(self):
        self.dirty = True
        self.cursor = getTimestamp()

    def getCursor(self):
        return self.cursor

    def getSaveRecord(self, path, data):
        return (path + SEPARATOR + SEPARATOR.join(data) + "\n")

    def isIndex(self, path):
        return path == self.index_file
    
    def addRecord(self, path, *args):
        if not self.records.has_key(path):
            self.records[path] = {}

        self.records[path]['values'] = args
        self.makeDirty()

    def removeRecord(self, path):
        if self.records.has_key(path) and self.records[path].has_key('values'):
            del self.records[path]['values']
            self.makeDirty()
        
    def getRecord(self, path):
        result = None
        if self.records.has_key(path) and self.records[path].has_key('values'):
            result = self.records[path]['values']

        return result
        
    def getKeys(self):
        return self.records.keys()
                     
    def getIndexPath(self):
        return self.index_path

    def getIndexFilePath(self):
        return self.indexDataFile




class FileIndex(KeyValuesStore):
    def __init__(self, path, index):
        KeyValuesStore.__init__(self, path, index)

    def addRecord(self, path, *args):
        KeyValuesStore.addRecord(self, path, *args)
        self.records[path]['last_transaction'] = ['add', getTimestamp()]

    def removeRecord(self, path):
        if self.records.has_key(path):
            KeyValuesStore.removeRecord(self, path)
            self.records[path]['last_transaction'] = ['del', getTimestamp()]

    def getFiles(self):
        result = []
        for path in self.getKeys():
            if self.getRecord(path) is not None:
                result.append(path)

        return result

    def getTransaction(self, path):
        result = None
        if self.records.has_key(path) and self.records[path].has_key('last_transaction'):
            result = self.records[path]['last_transaction']

        return result

    def clear(self):
        KeyValuesStore.clear(self)
        self.records = {}

    def removeTransaction(self, path):
        if self.records.has_key(path):
            del self.records[path]
            self.makeDirty()

    def getTransactions(self):
        transactions = {}
        for key,value in self.records.items():
            if value.has_key('last_transaction'):
                transactions[key] = value['last_transaction']

        return transactions

    def isLocked(self, path):
        timestamp = False
        if self.records.has_key(path) and self.records[path].has_key('locked'):
                timestamp = self.records[path]['locked']

        return timestamp

    def try_lock(self, path):
        result = False
        timestamp = None
        if self.records.has_key(path):
            timestamp = self.isLocked(path)
            if not timestamp:
                timestamp = getTimestamp()
                self.records[path]['locked'] = timestamp
                self.makeDirty()
                result = True
            else:
                timestamp = self.records[path]['locked']

        return result, timestamp

    def unlock(self, path):
        result = False
        if self.records.has_key(path):
            if self.records[path].has_key('locked'):
                del self.records[path]['locked']
                self.makeDirty()
                result = True

        return result

def test():
    from subprocess import call

    indexFile = "keyValuesStore.local"
    indexPath = "/tmp/"

    test1 = "/lissippetto.local"
    test2 = "/lisippettone.local"
    test3 = "/lisippettuzzo.local"
    
    index = FileIndex(indexPath, indexFile)

    index.addRecord(test1, "data1", "data2")
    index.addRecord(test2, "data123", "data12345", "data1234567")
    index.addRecord(test3, "data")

    assert index.isDirty() == True
    assert len(index.getTransactions()) != 0

    print "Index path is %s" % index.getIndexPath()
    print "Full index file path is %s" % index.getIndexFilePath()

    assert index.isIndex(indexFile)

    index.save()

    index.clear()
    assert len(index.getTransactions()) == 0
    assert len(index.getKeys()) == 0

    index.load()

    assert len(index.getKeys()) != 0

    print "Keys: %s" % str(index.getKeys())

    assert index.getRecord(test2) is not None
    index.removeRecord(test2)
    assert index.getRecord(test2) is None

    assert index.getRecord(test3) is not None

    ts = index.try_lock(test3)
    assert ts is not None

    assert index.unlock(test3) 

    call(["rm", os.path.join(indexPath, indexFile)])



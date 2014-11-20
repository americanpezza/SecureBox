import os, sys, traceback, time, shutil, re, base64
from datetime import datetime
import dropbox
from crypto.base import loadConfiguration

from sync.base import Synchronizer
from settings import CONFIG_DELAY, CONFIG_PATH, CONFIG_LOCAL_INDEX, CONFIG_DB, CONFIG_CURSOR, APP_PATH
from fileindex.base import getTimestamp
from fileindex.remote import RemoteIndex
from fileindex.local import LocalIndex

from crypto.file import EncryptedFile, EmbeddedEncryptedFile, EmbeddedPlainFile, EndOfFileException, FileMeta, FileMetaException
from crypto.exceptions import AuthenticationException
from dropbox.rest import RESTSocketError, ErrorResponse
from sync.actions import ActionFailedException

__author__ = 'pezza'



class SecureBox:
    def __init__(self):
        config,  crypt = loadConfiguration(CONFIG_DB)
        
        self.client = dropbox.client.DropboxClient(config['appToken'])
        self.crypt = crypt
        self.localIndex = LocalIndex(CONFIG_PATH, CONFIG_LOCAL_INDEX, APP_PATH)
        self.sync = Synchronizer(APP_PATH)
        self.recentlyUpdated = []

        self.cursor = None
        if os.path.exists(CONFIG_CURSOR):
            with open(CONFIG_CURSOR, 'r') as f:
                data = f.read()
                if data is not None and data != "":
                    try: 
                        self.cursor = data
                    except Exception, e:
                        pass

    def shutdown(self):
        self.localIndex.save()
        self.saveCursor()

    def monitor(self):
        while 1:
            try:
                self.spin()
            except RESTSocketError, e:
                m = re.search(".*\[Errno\s([-]*\d+)\].*", str(e))
                if m:
                    errno = int(m.groups()[0])
                    print "Can't connect to remote repository (error #%d), will try again later." % errno
                else:
                    print traceback.format_exc()              
            except Exception, e:
                print traceback.format_exc()
                print "Spin aborted, will retry later."

            time.sleep(CONFIG_DELAY)

    def spin(self):
        cursor, actions = self.buildTransaction()

        if len(actions) > 0:
            print "\nBuilt transaction with %d actions.\nRunning transaction..." % (len(actions))
            self.recentlyUpdated = self.apply(actions)
            print "\nTransaction completed."

        if cursor is not None:
            self.cursor = cursor

    def buildTransaction(self):
        cursor = None
        actions = self.buildLocalActions()
        if len(actions) == 0:
            cursor, actions = self.buildRemoteActions()

        return cursor, actions 

    def buildLocalActions(self):
        # handle local changes
        return self.sync.handleLocalChanges(self.localIndex, self.crypt)

    def buildRemoteActions(self):
        tree = {}
        removed = {}
        cursor = self.cursor
        counter = 0
        done = False

        while not done:
            result = self.client.delta(cursor)

            if result['reset']:
                print 'Delta has been reset'
                # TODO: Nuke directory
                #shutil.rmtree(APP_PATH)

            for path, metadata in result['entries']:
                if metadata is not None and metadata['is_dir']:
                    continue

                try:
                    decodedPath, meta = self.decodeEntry(path.upper())
                    if metadata is None:
                        # path has been removed
                        removed[decodedPath] = meta
                    else:
                        # path has been added
                        tree[decodedPath] = meta

                except AuthenticationException, e:
                    if metadata is not None:
                        print "Remote path failed authentication, ignored: %s" % path.upper()

                except FileMetaException, e:
                    if metadata is not None:
                        print "Remote path is not a valid filemeta, ignored: %s" % path.upper()

                except Exception,e:
                    print "Illegal file : %s" % path.upper()
                    print traceback.format_exc()

                counter += 1
                if counter % 50 == 0:
                    time.sleep(.05)

            cursor = result['cursor']

            if not result['has_more']:
                actions = []
                # handle remote deletions
                if len(removed.keys()) > 0:
                    actions.extend(self.sync.removePaths(removed, self.localIndex, self.crypt))

                # handle remote changes
                if len(tree.keys()) > 0:
                    actions.extend(self.sync.handleRemoteChanges(tree, self.localIndex, self.crypt))

                done = True

        return cursor, actions

    def decodeEntry(self, encodedPath):
        meta = self.convertPathToMeta(encodedPath.encode("utf8"))
        #data_key, salt, path, fileMod = meta.decryptMeta(self.crypt.keys[0])
        data_key, salt, path, fileMod = self.crypt.decryptMeta(meta)

        return path, meta

    def updateCursor(self, newCursor):
        # Update the cursor if necessary
        if self.cursor != newCursor:
            self.saveCursor(newCursor)
            self.cursor = newCursor

    def saveCursor(self, cur=None):
        if cur is None:
            cur = str(self.cursor)

        self._saveCursor(cur)

    def _saveCursor(self, cur=None):
        try:
            if cur is not None:
                with open(CONFIG_CURSOR, 'w') as f:
                    f.write(cur)
        except Exception, e:
            print traceback.format_exc()              

    def apply(self, actions):
        recently_seen = []
        counter = 0
        for action in actions:
            done = False

            while not done:
                try:
                    action.execute(self.client, self.localIndex)
                    for meta in action.getMetas():
                        if meta is not None:
                            recently_seen.append(meta.asUrl())

                    # save the new local index
                    if self.localIndex.isDirty():
                        self.localIndex.save()

                    done = True
                except Exception, e:
                    print traceback.format_exc()
                    time.sleep(.5)

            counter += 1
            print "* completed action %d of %d" % (counter, len(actions))

        return recently_seen

    def rebuild(self):
        def safelyRun(func, par):
            try:
                func(par)
            except Exception, e:
                pass

        # Remove the app_path
        safelyRun(shutil.rmtree, APP_PATH)

        # Recreate the app_path
        safelyRun(os.makedirs, APP_PATH)

        # Remove the cursor
        safelyRun(os.unlink, CONFIG_CURSOR)

        # Remove the index
        safelyRun(os.unlink, os.path.join(CONFIG_PATH, CONFIG_LOCAL_INDEX))

    def check(self):
        print "Check remote and local filesystems..."

        try:
            rootMeta = self.client.metadata('/')
            files = list()
            
            remoteMetas = []
            localMetas = []

            localFiles = self.sync.getLocalFiles()

            # build an index of metas
            metas = []
            for path in self.localIndex.getFiles():
                metas.append(self.localIndex.getFileMeta(path))

            count = 0
            for elem in rootMeta['contents']:
                #proceed = self.localIndex.has_metaFragment(elem['path'].lstrip('/'))
                #if not proceed:
                fragment = elem['path'].lstrip('/')
                found = False
                for m in metas:
                    if m.getMeta().startswith(fragment):
                        found = True
                        break

                if not found:
                   meta = self.rebuildMeta(elem['path'])
                   remoteMetas.append(meta)

                count += 1
                if count % 50 == 0:
                    sys.stdout.write(".")

            if len(remoteMetas) > 0:
                print "\nThe following files are stored remotely but not in our local index:"
                for meta in remoteMetas:
                    #dataKey, salt, path, mod = meta.decryptMeta(self.crypt.keys[0])
                    data_key, salt, path, mod = self.crypt.decryptMeta(meta)

                    moddate = datetime.utcfromtimestamp(mod)
                    print "* %s - added %s UTC" % (path, moddate)

            print

        except Exception, e:
            print traceback.format_exc() 

    def list(self):
        try:
            rootMeta = self.client.metadata('/')
            files = list()

            for elem in rootMeta['contents']:
                # for all the files except the index, DropBox has a hard limit to 25000 results
                if elem['is_dir']:
                    try:
                        path = self.processPath(elem['path'])
                        files.append(path)
                    except Exception, e:
                        print "Remote path %s failed decryption, ignored" % str(elem['path'])

            if len(self.localIndex.getFiles()) != len(files):
                print "\n*** Remote index size (%d) != actual remote files (%d)" % (len(self.localIndex.getFiles()), len(files))

        except Exception, e:
            print traceback.format_exc() 

    def processPath(self, remote_path):
        meta = self.rebuildMeta(remote_path)
        data_key, salt, path, mod = self.crypt.decryptMeta(meta)

        moddate = datetime.utcfromtimestamp(mod)
        print "* %s - added %s UTC" % (path, moddate)
                    
        indexMeta = self.localIndex.getFileMeta(path)

        if indexMeta is None: 
            print "*** Not in local index, index might be corrupt"
        else:
            indexDataKey, indexSalt, indexPath, indexMod = self.crypt.decryptMeta(indexMeta)
            if mod != indexMod:
                print "*** Timestamp in index is different (index: %s, remote: %s)" % (str(indexMod), str(mod))

        return path

    def convertPathToMeta(self, encodedPath):
        stringMeta = ''.join( encodedPath.encode("utf8").split('/'))
        return FileMeta(stringMeta)

    def rebuildMeta(self, folder):
        rootMeta = self.client.metadata(folder)
        if rootMeta.has_key('contents') and len(rootMeta['contents']) > 0:
            folder = rootMeta['contents'][0]['path']
            return self.rebuildMeta(folder)
        else:
            return self.convertPathToMeta(folder)

    def retrieve(self, url):
        pass

    def share(self, path):
        meta = self.localIndex.getFileMeta(path)
        if meta is None:
            print "File %s is not in SecureBox." % path
        else:
            try:
                remote_path = meta.asUrl()
                print "Url is %s" % remote_path
                response = self.client.media(remote_path)
                 
                result = {}
                result['meta'] = meta
                result['url'] = response['url']
                result['validity'] = response['expires']

                encrypted = self.crypt.dumps(result)
                print "\nURL: %s" % response['url']
                print "\nYou can share %s using the URL: %s\nThe URL will be valid until %s\n" % (path, base64.b32encode(encrypted), response['expires'])
            except ErrorResponse, er:
                status = er.status

                # generic error
                if status == 400 or status == 406:
                    print "Generic Dropbox error"
                    print traceback.format_exc()
                # not found
                elif status == 404:
                    print "File %s is in local index but not on remote dropbox. Possible bug?" % path
                else:
                    print traceback.format_exc()



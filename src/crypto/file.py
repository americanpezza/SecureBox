from Crypto.Cipher import AES
from functools import partial

from base import getCrypticle
import os, time, textwrap
import base64
from exceptions import EndOfFileException, FileMetaException, AuthenticationException

CHUNK_SIZE = 1024


__author__ = 'pezza'










def getLocalFileMod(path):
    return float(os.stat(path)[8])

def is_sequence(arg):
    return (not hasattr(arg, "strip") and
            hasattr(arg, "__getitem__") or
            hasattr(arg, "__iter__"))

class FileMeta:
    def __init__(self, param=None):
        self.meta = None
        self.wrapped_key = None
        self.salt = None
        self.keysig = None
        self.path = None
        self.fileMod = None
    
        if isinstance(param, basestring):
            try:
                self.decodeMeta(param)
            except Exception, e:
                raise FileMetaException("Illegal encoded meta: %s (%s)" % (param, str(e)))
                
        elif is_sequence(param) and len(param) == 5:
            try:
                self.encodeMeta(*param)
            except Exception, e:
                raise FileMetaException("Illegal values passed for fileMeta (%s): %s" % (str(param), str(e)))
        elif param is None:
            pass
        else:
            raise FileMetaException("Passed illegal param for fileMeta creation: %s" % str(param))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if other.meta == self.meta:
            return True
        else:
            return False

    def getMeta(self):
        return self.meta

    def getFileMod(self):
        return self.fileMod

    def getFilePath(self):
        return self.path

    def asUrl(self):
        path = textwrap.wrap(self.meta, 254)
        return '/' + '/'.join(path)

    def getElems(self):
        return [self.wrapped_key, self.salt, self.keysig, self.path, self.fileMod]

    def encodeMeta(self, wrapped_key, salt, keysig, path, fileMod):
        self.wrapped_key = wrapped_key
        self.salt = salt
        self.keysig = keysig
        self.path = path
        self.fileMod = fileMod
        
        self.meta = '$'.join([ 
            base64.b32encode(wrapped_key),
            base64.b32encode(salt),
            base64.b32encode(keysig),
            base64.b32encode(path),
            base64.b32encode(fileMod)
        ])

    def decodeMeta(self, meta):
        self.meta = meta
        wrapped_key, salt, keysig, path, mod = meta.split('$')
        
        self.wrapped_key = base64.b32decode(wrapped_key.upper())
        self.salt = base64.b32decode(salt.upper())
        self.keysig = base64.b32decode(keysig.upper())
        self.path = base64.b32decode(path.upper())
        self.fileMod = base64.b32decode(mod.upper())

    def encryptMeta(self, userKey, path, mod):
        # salt to be used for both data key encryption and file contents encryption        
        salt = os.urandom(16)

        # crypticle to be used for data key encryption
        fileInfoCrypt = getCrypticle(userKey, salt)
        
        # Generate data key
        data_key = fileInfoCrypt.generate_key()
        
        # Encrypt data for storage
        wrapped_key = fileInfoCrypt.encrypt(data_key)
        path = fileInfoCrypt.encrypt(path)
        fileMod = fileInfoCrypt.encrypt(str(mod))

        # Generate encrypted key signature for storage
        keysig = fileInfoCrypt.getHMAC(wrapped_key + path + fileMod)

        # setup internal encoded form
        self.encodeMeta(wrapped_key, salt, keysig.digest(), path, fileMod)

        return data_key, salt, keysig

    def decryptMeta(self, userKey):
        wrapped_key, salt, keysig, path, fileMod = self.getElems()

        # Create a cripticle for file metadata decoding
        fileInfoCrypt = getCrypticle(userKey, salt)
        
        # Test data signature
        test_keysig = fileInfoCrypt.getHMAC(wrapped_key + path + fileMod)
        if test_keysig.digest() != keysig:
            raise AuthenticationException("Signature authentication failed while decrypting fileMeta!")

        data_key = fileInfoCrypt.decrypt(wrapped_key)
        path = fileInfoCrypt.decrypt(path)
        mod = float(fileInfoCrypt.decrypt(fileMod))

        return data_key, salt, path, mod

    def __str__(self):
        return "Meta is %s\n Decoded as: \n key: %s\nsalt: %s\nkeysig: %s\npath: %s\nfileMod: %s" % (
            self.meta,
            base64.b32encode(self.wrapped_key),
            base64.b32encode(self.salt),
            base64.b32encode(self.keysig),
            base64.b32encode(self.path),
            base64.b32encode(str(self.fileMod))
        )

class PlainFile:
    def __init__(self, path, crypticle, root_path):
        """ path is the clear text path to the file to be encrypted """
        self.path = path
        self.root_path = root_path
        self.fileMod = getLocalFileMod(os.path.join(root_path, path))
        self.handle = None

        self.fileMeta = FileMeta()
        data_key, salt, sig = self.fileMeta.encryptMeta(crypticle.keys[0], self.path, self.fileMod)
        
        # crypticle to be used for file contents
        self.crypt = getCrypticle(data_key, salt)

        self.buffer = ""
        self.hmac = self.crypt.getHMAC(None, False)
        self.fileDone = False

    def __del__(self):
        try:
            if self.handle is not None:
                self.close()
        except Exception, e:
            pass

    def getFileMeta(self):
        return self.fileMeta
    
    def getFileMod(self):
        return self.fileMod

    def getFileFullPath(self):
        return os.path.join(self.root_path, self.path)

    def getFilePath(self):
        return self.path
    
    def open(self):
        if self.handle is None:
            self.handle = open(os.path.join(self.root_path, self.path), "rb")

    def close(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None
    
    def encrypt(self, handle):
        """ handle is a file-like object where the encrypted file contents will be written """
        if self.handle is None:
            self.open()

        done = False
        while not done:
            encryptedBlock = self._encryptChunk(self.hmac)
            if encryptedBlock:
                handle.write(encryptedBlock)
            else:
                done = True
   
    def _encryptChunk(self, sig):
        data = self.handle.read(CHUNK_SIZE)
        if data:
            data = self.crypt.encrypt(data, sig)
        
        return data

    def read(self, bytes=None):
        if self.handle is None:
            self.open()

        if bytes is None:
            return self._read()
        else:
            return self._readBytes(bytes)

    def _read(self):
        done = False
        buffer = ""

        while not done:
            data = self._encryptChunk(self.hmac)
            if data:
                buffer = buffer + data
            else:
                self.close()
                done = True

        return buffer

    def _readBytes(self, bytes):
        if not self.fileDone:
            while len(self.buffer) < bytes:
                data = self._encryptChunk(self.hmac)
                if data:
                    self.buffer = self.buffer + data
                else:
                    self.fileDone = True
                    break

        result = False
        if len(self.buffer) > 0:
            length = bytes
            if len(self.buffer) < bytes:
                length = len(self.buffer)

            result = self.buffer[:length]
            self.buffer = self.buffer[length:]
        else:
            self.close()
            raise EndOfFileException("End of file")

        return result

class EmbeddedPlainFile(PlainFile):
    def __init__(self, path, crypt, root):
        PlainFile.__init__(self, path, crypt, root)    
        self.embedDone = False

    def read(self, bytes=None):
        if self.handle is None:
            self.open()
        
        # Embed the fileMeta in the first line of the encrypted file
        if not self.embedDone:
            self.buffer = self.getFileMeta().getMeta() + '\n'
            self.embedDone = True
            
        return PlainFile.read(self, bytes)        

    def encrypt(self, handle):
        if self.handle is None:
            self.open()

        # save fileMeta inside the file
        handle.write(self.fileMeta.getMeta() + '\n')
        self.embedDone = True
            
        PlainFile.encrypt(self, handle)

class EncryptedFile:
    def __init__(self, fileMeta, crypticle, root_path):
        """ fileMeta is the encrypted metadata of the file to be decrypted """
        self.handle = None
        self.root_path = root_path
        self.userCrypt = crypticle
        self.path = None
        
        self.fileMeta = FileMeta(fileMeta)
        self.setup()

    def setup(self):
        data_key, salt, path, fileMod = self.fileMeta.decryptMeta(self.userCrypt.keys[0])

        self.path = path
        self.fileMod = fileMod

        # Create a crypticle for file contents decoding
        self.crypt = getCrypticle(data_key, salt)    

    def __del__(self):
        try:
            if self.handle is not None:
                self.close()
        except Exception, e:
            pass

    def open(self):
        if self.handle is None:
            # Make sure the intermediate folders are created
            full_path = os.path.join(self.root_path, self.path)
            rel_path = os.path.dirname(full_path)
            try:
                os.makedirs(rel_path)
            except Exception, e:
                pass

            self.handle = open(os.path.join(self.root_path, self.path), "wb")

    def close(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None

    def getFilePath(self):
        return self.path

    def getFileFullPath(self):
        return os.path.join(self.root_path, self.path)

    def getFileMeta(self):
        return self.fileMeta

    def getFileMod(self):
        return self.fileMod
        
    def decrypt(self, handle):
        """ handle is a file-like object where the encrypted contents can be read for decryption """
        if self.handle is None:
            self.open()
        
        sig = self.crypt.getHMAC(None, False)
        while True:
            data = handle.read(CHUNK_SIZE + 64)
            if data:
                decryptedBlock = self.crypt.decrypt(data, sig)        
                self.handle.write(decryptedBlock)
            else:
                break

class EmbeddedEncryptedFile(EncryptedFile):
    def __init__(self, crypticle, root_path, local_path):
        self.handle = None
        self.root_path = root_path
        self.userCrypt = crypticle
        self.fileMeta = None
        self.path = local_path

    def decrypt(self, handle):
        if self.handle is None:
            self.open()

        # start by getting the filemeta        
        self.retrieveFileMeta(handle)
        self.setup()
        EncryptedFile.decrypt(self, handle)
        
    def retrieveFileMeta(self, handle):
        line = ''
        for char in iter(partial(handle.read, 1), ''):
            if char == "\n":
                break
            else:
                line = line + char
        
        self.fileMeta = FileMeta(line)





def test():
    from subprocess import call
    root_path = "/tmp"
    path_plain = "plainFile.txt"
    path_encrypted = "encryptedFile.txt"
    path_plain_check = "plainFileOriginal.txt"
    
    password = "pippopippo"
    salt = "mysalt"
    
    crypt = getCrypticle(password, salt)

    
   testFileSize = (16 * 1024 * 1024)
   testFileContent = "Sopra la campa la capra crepa, Sotto la Panca la capra campa"
   testFileLines = testFileSize / (len(testFileContent) + 1)


   print "Generating a %s byte-byte long test file..." % testFileSize
   with open(os.path.join(root_path, path_plain), "w") as f:
       for i in range(0,testFileLines):
           f.write(testFileContent + "\n")

   call(["cp",os.path.join(root_path, path_plain), os.path.join(root_path, path_plain_check)])

   filesize = os.path.getsize( os.path.join(root_path, path_plain_check))

   start = time.time()

    
    
    
    
    
    
    print "Testing with a %d bytes files..." % filesize
    
    print "\nUsing dropbox file containers"
    
    # created encrypting file object
    print "- Encrypting..."
    fileObj = PlainFile(path_plain, crypt, root_path)
    with open(os.path.join(root_path, path_encrypted), "w") as f:
        fileObj.encrypt(f)
        
    meta = fileObj.getFileMeta().getMeta()
    fileObj.close()
    
    encryption = time.time()
    
    print "- Decrypting..."
    fileObj = EncryptedFile(meta, crypt, root_path)
    with open(os.path.join(root_path, path_encrypted), "r") as f:
        fileObj.decrypt(f)
    
    fileObj.close()
    
    decryption = time.time()
    
    call(['diff', os.path.join( root_path, path_plain ), os.path.join(root_path, path_plain_check)])
    
    
    print "++ Timing: encryption %f (%d KB/sec), decryption: %f (%d KB/sec)" % ( 
        encryption - start,
        int((filesize / (encryption - start)) / 1024.0),
        decryption - encryption,
        int((filesize / (decryption - encryption)) / 1024.0)
     ) 
    
    



    print "\nNow try with streamed reads..."

    start = time.time()
    
    # created encrypting file object
    print "- Encrypting..."
    fileObj = PlainFile(path_plain, crypt, root_path)
    f = open(os.path.join(root_path, path_encrypted), "w")
    d = fileObj.read()
    f.write(d)
    f.close()

    with open(os.path.join(root_path, path_encrypted), "w") as f:
        done = False
        while not done:
            try:
                chunk = fileObj.read(CHUNK_SIZE)
                if chunk:
                    f.write(chunk)
            except Exception, e:
                done = True
        
    meta = fileObj.getFileMeta().getMeta()
    fileObj.close()
    
    encryption = time.time()
    
    print "- Decrypting..."
    fileObj = EncryptedFile(meta, crypt, root_path)
    with open(os.path.join(root_path, path_encrypted), "r") as f:
        fileObj.decrypt(f)
    
    fileObj.close()
    
    decryption = time.time()
    
    call(['diff', os.path.join( root_path, path_plain ), os.path.join(root_path, path_plain_check)])
    
    
    print "++ Timing: encryption %f (%d KB/sec), decryption: %f (%d KB/sec)" % ( 
        encryption - start,
        int((filesize / (encryption - start)) / 1024.0),
        decryption - encryption,
        int((filesize / (decryption - encryption)) / 1024.0)
     ) 






    print "\nNow try with embedded files..."

    start = time.time()
    
    # created encrypting file object
    print "- Encrypting..."
    fileObj = EmbeddedPlainFile(path_plain, crypt, root_path)
    with open(os.path.join(root_path, path_encrypted), "w") as f:
        fileObj.encrypt(f)

    meta = fileObj.getFileMeta().getMeta()
    fileObj.close()
    
    encryption = time.time()
    
    print "- Decrypting..." 
    fileObj = EmbeddedEncryptedFile(crypt, root_path, path_plain)
    with open(os.path.join(root_path, path_encrypted), "r") as f:
        fileObj.decrypt(f)
    
    fileObj.close()
    
    decryption = time.time()
    
    call(['diff', os.path.join( root_path, path_plain ), os.path.join(root_path, path_plain_check)])
    
    
    print "++ Timing: encryption %f (%d KB/sec), decryption: %f (%d KB/sec)" % ( 
        encryption - start,
        int((filesize / (encryption - start)) / 1024.0),
        decryption - encryption,
        int((filesize / (decryption - encryption)) / 1024.0)
     ) 
    
    
    
    
    print "\nNow try with streamed embedded reads..."

    start = time.time()
    
    # created encrypting file object
    print "- Encrypting..."
    fileObj = EmbeddedPlainFile(path_plain, crypt, root_path)
    with open(os.path.join(root_path, path_encrypted), "w") as f:
        done = False
        while not done:
            try:
                chunk = fileObj.read(CHUNK_SIZE)
                if chunk:
                    f.write(chunk)
            except EndOfFileException, e:
                done = True
            except Exception, e:
                print "Error: %s", e

    meta = fileObj.getFileMeta().getMeta()
    fileObj.close()
    
    encryption = time.time()
    
    print "- Decrypting..."
    fileObj = EmbeddedEncryptedFile(crypt, root_path, path_plain)
    with open(os.path.join(root_path, path_encrypted), "r") as f:
        fileObj.decrypt(f)
    
    fileObj.close()
    
    decryption = time.time()
    
    result = call(['diff', os.path.join( root_path, path_plain ), os.path.join(root_path, path_plain_check)])
    assert result == 0

    print "++ Timing: encryption %f (%d KB/sec), decryption: %f (%d KB/sec)" % ( 
        encryption - start,
        int((filesize / (encryption - start)) / 1024.0),
        decryption - encryption,
        int((filesize / (decryption - encryption)) / 1024.0)
     )
    
    
    
    call(["rm", os.path.join(root_path, path_encrypted)])
    call(["rm", os.path.join(root_path, path_plain)])
    call(["rm", os.path.join(root_path, path_plain_check)])
    
    
    print "\nDone.\n\n"
    


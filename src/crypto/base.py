import os,  aes
from getpass import getpass
from pbkdf2 import PBKDF2


__author__ = 'pezza'

# Crypto strategies available
# The first value is the key size (in bytes), the second is the hash size (in bytes)
cryptStrategies = { 
    'aes128': [
                16, # 16 * 8 = 128 bits key
                32  # 32 * 8 = 256 bits SHA hash
            ], 
    'aes256': [ 
                32, # 32 * 8 = 256 bits key 
                64  # 64 * 8 = 512 bits SHA hash
            ]
}
cryptStrategy = 'aes128'




def getStrategy():
    global cryptStrategy

    return cryptStrategy

def setStrategy(strategy):
    global cryptStrategy, cryptStrategies

    if strategy in cryptStrategies.keys():
        cryptStrategy = strategy
    else:
        raise Exception("Unknown strategy: %s" % strategy)

def getCrypticle(pwd,  salt):
    global cryptStrategy, cryptStrategies

    keysize = cryptStrategies[cryptStrategy][0] + cryptStrategies[cryptStrategy][1]
    key = PBKDF2(pwd, salt).read(keysize).encode("base64").replace("\n", "")
    crypt = aes.Crypticle(key)
    
    return crypt

def saveConfiguration(config, output_path,  pwd=None):
    password = pwd
    if password is None:
        password = getpass('Enter your master password: ')

    salt = os.urandom(8)
    crypt = getCrypticle(password,  salt)
    encrypted = crypt.dumps(config)
    
    with open(output_path, 'wb') as f:
        f.write(salt + encrypted)
    
def loadConfiguration(input_path,  pwd=None):
    password = pwd
    if password is None:
        password = getpass('Enter your master password: ')

    with open(input_path, 'rb') as f:
        salt = f.read(8)
        encrypted_text = f.read()

    crypt = getCrypticle(password,  salt)
    config = crypt.loads(encrypted_text)

    return config, crypt

SecureBox
============

### Introduction
A convenient way to manage encryption for Dropbox (and potentially, any cloud-based file storage system).

The main use case is simple:
* a folder on your device contains files you want to sync with a cloud-based storage
* you want to keep editing and managing your files locally
* you want to achieve a "zero-knowledge" guarantee, e.g. make sure that the cloud stoarge admins are unable to access your files
* you want to achieve confidentiality and integrity for data at rest (e.g. once stored remotely) and on the go (e.g. while being transmitted over the network)

The app works as a python daemon that monitors a file folder for changes. When a change is detected either locally or remotely, the daemon will synchronize the changes.
The sync algorithm attemps to take decisions based on the timestamp of the uploaded files and keeps a ledger of the synchrnoized files.
Any information stored on the device (such as the remote storage authentication keys, statues, etc...) is encrypted. Both the authentication info and the synchronized files are encrypted with a password: the user has to enter his password every time the daemon is started or stopped.
The user password is never stored either locally or remotely.

The encryption algorithm used is AES-128 with a HMAC based on SHA1-256 to ensure message integrity.
The code is structured in such a way that changing encryption scheme (e.g. moving to AES-256 and/or SHA1-512) should be achieved with minimal changes.

The only supported storage at the moment is Dropbox. Adding additional storage services (e.g. GoogleDrive, Microsoft Skydrive, etc...) should be easily achieved.

### Security assumptions
The main idea behind SecureBox is to consider:
* the local device as "secure". THe entire remote folder is synchronized and thus decrypted and saved. The only exception is the app keys, which are stored locally in an encrypted ocntainer
* the link between the device and the remote storage as insecure. This is mitigated by using a secure connection (SSL) and encrypting all content before sending it over the wire
* the remote storage as insecure. Anything stored remotely is encrypted

The use of AES-128 grants a reasonable security encryption, for the highest standard the app should be moved to AES-256.

### Supported Operating Systems

The app has been developed and tested under Mac OSX 10.9 and Linux (Ubuntu 14.04 and Mint 17). It's entirely based on python, and any attempt has been done to preserve platform independence.

### Setup

1. Install `pip` from your distribution's package manager. On RHEL-based distributions this is done through `yum install python -pip`, on Ubuntu `sudo apt-get install python-pip`
2. Install python-dev, in order to support compilation of the crypto libraries. On linux, you can use `yum install python-dev` for RHEL-based or `apt-get install python-dev` for Ubuntu-based
3. Install the required dependencies using `pip install -r requirements.txt`. 
4. Go to https://www.dropbox.com/developers/apps/create and create a new application. Here are the options you will 
   need to select
   1. What type of app do you want to create? - Dropbox API app
   2. What type of data does your app need to store on Dropbox? - Files and datastores
   3. Can your app be limited to its own, private folder? - Yes My app only needs access to files it creates.
5. Run `python src/securebox.py --configure` and follow the prompts. 

### Usage

The help option is pretty self explanatory.

```
$ ./securebox -h
usage: securebox [-h]
                 {start,stop,list,restart,check,rebuild,configure,share} ...

positional arguments:
  {start,stop,list,restart,check,rebuild,configure,share}
                        Commands
    start               Start SecureBox
    stop                Stop SecureBox
    list                List files in SecureBox
    restart             Restart SecureBox
    check               Check local index with remote files
    rebuild             Rebuild the index from the remote folder contents
                        (DropBox API limited to 25000 files)
    configure           Configure the application
    share               Create a publicly available link to a file in the
                        SecureBox

optional arguments:
  -h, --help            show this help message and exit
```

### Disclaimer

```
THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

### Credits

* https://cryptography.io : a python encryption library with a modern approach to encryption. Even if it's not used in the app, some ideas are taken from here
* https://github.com/americanpezza/pyDropSecure : a basic ecnryption/decryption script supporting storage on DropBox
* http://security.stackexchange.com/questions/57498/asymmetric-data-storage-no-hash-password-storage : A discussion on how to store data in a database with symmetric encryption and salting
* http://code.activestate.com/recipes/576980-authenticated-encryption-with-pycrypto/ : most of the encryption code is based on this very handy little snippet, modified to use a 256 bit key instead of 192 bit key

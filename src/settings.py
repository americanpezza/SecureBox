import os

__author__ = 'Pezza'





config = {
    'appKey': None, 
    'appSecret': None, 
    'appToken': None, 
    'userId': None
}

APP_PATH = os.path.join(os.path.expanduser('~'), 'SecureBox')

# The delay between remote polling
CONFIG_DELAY = 3

# The config settings folder
CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.securebox')

# The pidfile
PIDFILE = os.path.join(CONFIG_PATH, "securebox.pid")

# The encrypted container with the connection token and other DropBox attributes
CONFIG_DB = os.path.join(CONFIG_PATH, 'config.db')

# The cursor for DropBox polling
CONFIG_CURSOR = os.path.join(CONFIG_PATH, 'cursor')

# The local index file
CONFIG_LOCAL_INDEX = '___lcl_index___'

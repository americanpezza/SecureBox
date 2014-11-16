#!/usr/bin/env python -u

import argparse
import os,  sys
import configure
from settings import APP_PATH, CONFIG_DB, config, PIDFILE, CONFIG_PATH
from service.watcher import Watcher
from repo.dropbox.proc import SecureBox

__author__ = 'pezza'





def createService(db, pidfile):
    logfile = os.path.join(CONFIG_PATH, "securebox.log")
    return Watcher(db, PIDFILE, "/dev/null", logfile, logfile) 



if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--start', help='Start the script',
                        action='store_true')

    action.add_argument('--stop', help='Stop the script',
                        action='store_true')

    action.add_argument('--restart', help='Restart the script',
                        action='store_true')

    action.add_argument('--list', help='List files in SecureBox',
                        action='store_true')

    action.add_argument('--check', help='Check local index with remote files',
                        action='store_true')

    action.add_argument('--rebuild', help='Rebuild the index from the remote folder contents (DropBox API limited to 25000 files)',
                        action='store_true')

    action.add_argument('--export', help='Export application keys',
                        dest='export')

    action.add_argument('--import', help='Import application keys',
                        dest='imp')

    action.add_argument('--configure', help='Configure the application',
                        action='store_true')
    args = parser.parse_args()

    if args.export is not None:
        configure.export_configuration(args.export)

    elif args.imp is not None:
        configure.import_configuration(args.imp)

    elif args.list:
        db = SecureBox()
        db.list()

    elif args.check:
        db = SecureBox()
        db.check()

    elif args.rebuild:
        choice = "n"
        if os.path.exists(CONFIG_DB):
            while 1:
                choice = raw_input('This will destroy the local folder contents and other state information of the local repository and exit. Next time SecureBox is started, it will downlaod the whole repository and start fresh.\nAre you sure you want to continue? (Y/n)')

                if choice == 'Y' or choice == 'n':
                    break
 
        if choice == 'Y':
            db = SecureBox()
            db.rebuild()

    elif args.configure:
        if not os.path.exists(APP_PATH):
            os.makedirs(APP_PATH)

        choice = "Y"
        if os.path.exists(CONFIG_DB):
            while 1:
                choice = raw_input('Configuration file exists. '
                                   'Do you want to overwrite? (Y/n)')

                if choice == 'Y' or choice == 'n':
                    break
 
        if choice == 'Y':
            configure.new_configuration()

    else:
        db = SecureBox()

        if args.start:
            daemon = createService(db, PIDFILE)
            daemon.start()

        elif args.stop:
            daemon = createService(db, PIDFILE)
            daemon.stop()

        elif args.restart:
            daemon = createService(db, PIDFILE)
            daemon.restart()
        

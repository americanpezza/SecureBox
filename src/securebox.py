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
    subparsers = parser.add_subparsers(dest='operation', help='Commands')

    # Start
    start_parser = subparsers.add_parser('start', help="Start SecureBox")

    # Stop
    stop_parser = subparsers.add_parser('stop', help="Stop SecureBox")

    # List
    list_parser = subparsers.add_parser('list', help="List files in SecureBox")

    # Restart
    restart_parser = subparsers.add_parser('restart', help="Restart SecureBox")

    # Check
    check_parser = subparsers.add_parser('check', help="Check local index with remote files")

    # Rebuild
    rebuild_parser = subparsers.add_parser('rebuild', help="Rebuild the index from the remote folder contents (DropBox API limited to 25000 files)")

    # Configure
    configure_parser = subparsers.add_parser('configure', help="Configure the application")

    # Share a link to a file
    share_parser = subparsers.add_parser('share', help="Create a publicly available link to a file in the SecureBox")
    share_parser.add_argument('path', action='store', help="The file path to create a link to")


    #action.add_argument('--export', help='Export application keys',
    #                    dest='export')

    #action.add_argument('--import', help='Import application keys',
    #                    dest='imp')

    args = parser.parse_args()
    operation = args.operation

    if operation == "share":
        db = SecureBox()
        db.share(args.path)

    elif operation == "export":
        configure.export_configuration(args.export)

    elif operation == "import":
        configure.import_configuration(args.imp)

    elif operation == "list":
        db = SecureBox()
        db.list()

    elif operation == "check":
        db = SecureBox()
        db.check()

    elif operation == "rebuild":
        choice = "n"
        if os.path.exists(CONFIG_DB):
            while 1:
                choice = raw_input('This will destroy the local folder contents and other state information of the local repository and exit. Next time SecureBox is started, it will downlaod the whole repository and start fresh.\nAre you sure you want to continue? (Y/n)')

                if choice == 'Y' or choice == 'n':
                    break
 
        if choice == 'Y':
            db = SecureBox()
            db.rebuild()

    elif operation == "configure":
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

    elif operation == "start":
        db = SecureBox()
        daemon = createService(db, PIDFILE)
        daemon.start()

    elif operation == "stop":
        db = SecureBox()
        daemon = createService(db, PIDFILE)
        daemon.stop()

    elif operation == "restart":
        db = SecureBox()
        daemon = createService(db, PIDFILE)
        daemon.restart()
        

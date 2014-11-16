import os, sys
from daemon import Daemon
from settings import CONFIG_CURSOR
from signal import *


__author__ = 'pezza'


class Watcher(Daemon):
    def __init__(self,  db,  *args,  **kwargs):
        Daemon.__init__(self,  *args,  **kwargs)
        self.db = db
        
    def run(self):
        def cleanup(*args):
            if self.db.cursor is not None:
                self.db.saveCursor()
            self.db.shutdown()

            sys.exit(0)

        # register the cleanup function with all signals
        for sig in (SIGABRT, SIGINT, SIGTERM):
            signal(sig, cleanup)

        self.db.monitor()

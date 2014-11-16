#!/usr/bin/python

import fileindex.local
import fileindex.remote
import crypto.file


print "\n\n\n**** testing fileindex.remote..."
fileindex.remote.test()
print "\n\n\n**** testing fileindex.base..."
fileindex.base.test()
print "\n\n\n**** testing fileindex.local..."
fileindex.local.test()
print "\n\n\n**** testing crypto..."
crypto.file.test()

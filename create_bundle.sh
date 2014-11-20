#!/bin/bash

# bundle name
bundlename="SecureBox.tar.gz"

# target dir
dirname="SecureBox/distrib"

mkdir $dirname

cd ..
find SecureBox/src -name "*.py" | xargs tar -cvzf "$dirname/$bundlename" SecureBox/README.md SecureBox/LICENSE SecureBox/requirements.txt SecureBox/install_macosx.sh

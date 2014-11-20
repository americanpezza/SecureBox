#!/bin/bash



targetfolder="/usr/local/share/SecureBox"

# Ensure /share is available
sudo mkdir /usr/local/share

# Create main folder
sudo mkdir $targetfolder

# Copy app
sudo cp -r . $targetfolder

# Install pip
sudo easy_install pip

# Install dependencies
sudo pip install -r requirements.txt

# Create SecureBox folders
mkdir ~/.securebox
mkdir ~/SecureBox

# Link inside command path
sudo ln -s "$targetfolder/src/securebox.py" /usr/local/bin/securebox

echo "Done."



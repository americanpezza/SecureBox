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

echo "Done."



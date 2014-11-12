#!/bin/bash

# Parameter check
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Syntax: $0 <source directory> <data directory>"
    exit 1
fi

# Repository check
if [ ! -d "$1/.git" ]; then
    echo "This script can only downgrade Headphones installations via Git."
    exit 1
fi

# Version file check
if [ ! -s "$2/version.lock" ]; then
    echo "Missing the version.lock file in the data folder, or the file is empty. Did you start Headphones at least once?"
    exit 1
fi

# Git installation check
if [ ! -x "$(command -v wget)" ]; then
    echo "Git is required to downgrade."
    exit 1
fi

# Display information
HASH=$(cat $2/version.lock)

echo "This script will try to downgrade Headphones to the last version that started, version $HASH. Make sure you have a backup of your config file and database, just in case!"
echo "Press enter to continue, or CTRL + C to quit."
read

# Downgrade
cd "$1"
git reset --hard "$HASH"

echo "All done, Headphones should be downgraded to the last version that started."
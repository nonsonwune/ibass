#!/bin/bash

# Script to force sync changes from the original repository to the fork

# Change to the directory of the original repository
# Replace '/Users/nonsonwune/Desktop/personal_projects/ibass1' with the actual path to the original repository
cd /Users/nonsonwune/Desktop/personal_projects/ibass1 || exit

# Ensure we're on the main branch
git checkout main

# Pull the latest changes from the original repository
git pull origin main

# Force push the changes to your fork
# This will override any changes in the fork with the state of the original repository
git push -f https://github.com/jambgpt/naija-uni-finder.git main

echo "Repository sync completed. Changes force pushed to fork."
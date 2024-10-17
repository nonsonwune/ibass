#!/bin/bash

# Ensure you're in your dev branch
git checkout dev

# Commit any pending changes
git add .
git commit -m "Update bookmark for persistent bookmark icon activate"

# Switch to the main branch
git checkout main

# Merge the dev branch into main
git merge dev

# Push the updated main branch to the remote repository
git push origin main
#!/bin/bash

# Ensure you're in your dev branch
git checkout dev

# Commit any pending changes
git add .
<<<<<<< HEAD
git commit -m "Update bookmark for persistent bookmark icon activate"
=======
git commit -m "Fix email verification error and improve error handling

- Replace db.session.get() with User.query.filter_by() in verify_email function
- Add check for non-existent user during email verification
- Improve error messaging for invalid or expired verification links"
>>>>>>> dev

# Switch to the main branch
git checkout main

# Merge the dev branch into main
git merge dev

# Push the updated main branch to the remote repository
git push origin main
// app/static/js/main.js

document.addEventListener("DOMContentLoaded", function () {
  console.log("Initializing application...");
  initializeTooltips();
  initializeCommentSystem();
  initializeVoting();
  initializeInstitutionModal();
  initializeBookmarkSystem();

  if (window.isAuthenticated) {
    fetchUserVotes();
    fetchUserBookmarks();
  }
});

// app/static/js/contact.js

document.addEventListener("DOMContentLoaded", function () {
  // Initialize functionalities
  initializeCommentSystem();
  initializeVoting();
  initializeTooltips();

  if (window.isAuthenticated) {
    fetchUserVotes();
  }

  // Add smooth parallax effect
  window.addEventListener("scroll", function () {
    const scrolled = window.pageYOffset;
    const background = document.querySelector(".contact-background");
    if (background) {
      background.style.backgroundPositionY = -(scrolled * 0.5) + "px";
    }
  });

  // Fix CSRF token initialization
  window.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
});

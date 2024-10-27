// app/static/js/comments.js

function initializeCommentSystem() {
  const commentTextarea = document.getElementById("comment");
  const charCount = document.getElementById("charCount");

  if (commentTextarea && charCount) {
    commentTextarea.addEventListener("input", function () {
      const remaining = 200 - this.value.length;
      charCount.textContent = `${remaining} remaining`;
      charCount.classList.toggle("text-danger", remaining < 20);
    });
  }
}

// Expose function globally
window.initializeCommentSystem = initializeCommentSystem;

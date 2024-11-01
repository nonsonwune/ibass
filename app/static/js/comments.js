// app/static/js/comments.js

document.addEventListener("DOMContentLoaded", function () {
  initializeCommentSystem();
  initializeVoting();
  initializeTooltips();

  if (window.isAuthenticated) {
    fetchUserVotes();
  }

  initializeReplySystem(); // Ensure it's called only once here
});

/**
 * Initializes the comment system by setting up character count and form validation.
 */
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

  // Handle form submission validation
  const commentForm = document.querySelector(".comment-form");
  if (commentForm) {
    commentForm.addEventListener("submit", function (event) {
      if (!commentTextarea.value.trim()) {
        event.preventDefault();
        commentTextarea.classList.add("is-invalid");
      } else {
        commentTextarea.classList.remove("is-invalid");
      }
    });
  }
}

/**
 * Initializes voting functionality by setting up event listeners on vote buttons.
 */
function initializeVoting() {
  const voteButtons = document.querySelectorAll(".vote-btn");
  voteButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      if (!window.isAuthenticated) {
        window.location.href = "/auth/login";
        return;
      }
      const commentId = this.getAttribute("data-comment-id");
      const action = this.getAttribute("data-vote-type");
      vote(commentId, action, this);
    });
  });
}

/**
 * Handles the voting logic by sending AJAX requests to the backend.
 * @param {number} commentId - The ID of the comment being voted on.
 * @param {string} action - The type of vote ('like' or 'dislike').
 * @param {HTMLElement} buttonElement - The button element that was clicked.
 */
function vote(commentId, action, buttonElement) {
  if (buttonElement.disabled) {
    return;
  }

  const commentElement = buttonElement.closest(".comment-card");
  if (!commentElement) {
    showToast("Error finding comment element", "danger");
    return;
  }

  const buttons = {
    like: commentElement.querySelector('[data-vote-type="like"]'),
    dislike: commentElement.querySelector('[data-vote-type="dislike"]'),
  };

  const loadingSpinner =
    '<span class="spinner-border spinner-border-sm me-1" role="status"></span>';
  buttons[action].innerHTML =
    loadingSpinner + (action === "like" ? "Liking..." : "Disliking...");
  Object.values(buttons).forEach((btn) => (btn.disabled = true));

  fetch(`/api/vote/${commentId}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": window.csrfToken,
      Accept: "application/json",
    },
    credentials: "same-origin",
  })
    .then(async (response) => {
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to process vote");
      }
      return response.json();
    })
    .then((data) => {
      if (!data.success) {
        throw new Error(data.message || "Vote not recorded");
      }

      updateVoteUI(commentElement, data);

      // Update the button innerHTML with the new like/dislike counts
      if (buttons.like && buttons.dislike) {
        buttons.like.innerHTML =
          '<i class="fas fa-thumbs-up me-1"></i> <span class="like-count">(' +
          data.likes +
          ")</span>";
        buttons.dislike.innerHTML =
          '<i class="fas fa-thumbs-down me-1"></i> <span class="dislike-count">(' +
          data.dislikes +
          ")</span>";
      }

      showToast(data.message || "Vote recorded successfully", "success");
    })
    .catch((error) => {
      console.error("Vote error:", error);
      showToast(error.message || "Error processing vote", "danger");
    })
    .finally(() => {
      if (buttons.like && buttons.dislike) {
        buttons.like.disabled = false;
        buttons.dislike.disabled = false;
      }
      fetchUserVotes();
    });
}

/**
 * Updates the UI to reflect the new vote counts and user vote status.
 * @param {HTMLElement} commentElement - The comment card element.
 * @param {Object} data - The response data from the backend.
 */
function updateVoteUI(commentElement, data) {
  const likeButton = commentElement.querySelector('[data-vote-type="like"]');
  const dislikeButton = commentElement.querySelector(
    '[data-vote-type="dislike"]'
  );

  if (likeButton) {
    const likeCount = likeButton.querySelector(".like-count");
    if (likeCount) {
      likeCount.textContent = `(${data.likes})`;
    }
    likeButton.classList.remove("active");
    if (data.user_vote === "like") {
      likeButton.classList.add("active");
    }
  }

  if (dislikeButton) {
    const dislikeCount = dislikeButton.querySelector(".dislike-count");
    if (dislikeCount) {
      dislikeCount.textContent = `(${data.dislikes})`;
    }
    dislikeButton.classList.remove("active");
    if (data.user_vote === "dislike") {
      dislikeButton.classList.add("active");
    }
  }

  if (
    typeof data.user_id === "number" &&
    typeof data.user_score === "number"
  ) {
    document
      .querySelectorAll(`.user-score[data-user-id="${data.user_id}"]`)
      .forEach((el) => (el.textContent = data.user_score));
  }
}

/**
 * Fetches the user's existing votes from the backend.
 */
function fetchUserVotes() {
  fetch("/api/user_votes", {
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": window.csrfToken,
      Accept: "application/json",
    },
  })
    .then((response) => {
      if (response.redirected || response.status === 401) {
        console.log("User not authenticated");
        return null;
      }
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data) {
        applyUserVotes(data);
      }
    })
    .catch((error) => {
      console.error("Error fetching user votes:", error);
    });
}

/**
 * Applies the user's existing votes to the UI.
 * @param {Object} votes - An object mapping comment IDs to vote types.
 */
function applyUserVotes(votes) {
  if (!votes) return;
  document.querySelectorAll(".vote-btn").forEach((button) => {
    const commentId = button.getAttribute("data-comment-id");
    const voteType = button.getAttribute("data-vote-type");

    button.classList.remove("active");
    if (votes[commentId] === voteType) {
      button.classList.add("active");
    }
  });
}

/**
 * Initializes Bootstrap tooltips.
 */
function initializeTooltips() {
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.forEach(function (tooltipTriggerEl) {
    new bootstrap.Tooltip(tooltipTriggerEl);
  });
}

/**
 * Displays a Bootstrap toast notification.
 * @param {string} message - The message to display.
 * @param {string} type - The type of toast ('success', 'danger', 'info', etc.).
 */
function showToast(message, type = "info") {
  const toastContainer = document.getElementById("toastContainer");
  if (!toastContainer) return;

  const toastElement = document.createElement("div");
  toastElement.className = `toast align-items-center text-white bg-${type} border-0`;
  toastElement.setAttribute("role", "alert");
  toastElement.setAttribute("aria-live", "assertive");
  toastElement.setAttribute("aria-atomic", "true");

  toastElement.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        ${message}
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  toastContainer.appendChild(toastElement);
  const toast = new bootstrap.Toast(toastElement, {
    autohide: true,
    delay: 3000,
  });
  toast.show();

  toastElement.addEventListener("hidden.bs.toast", () => {
    toastElement.remove();
  });
}

/**
 * Initializes the reply system by setting up event listeners for reply buttons and reply submissions.
 */
function initializeReplySystem() {
  const replyModal = document.getElementById('replyModal');
  
  if (!replyModal) {
    console.error('Reply modal not found in DOM');
    return;
  }

  const modal = new bootstrap.Modal(replyModal);
  let currentCommentId = null;

  // Handle reply button clicks
  document.querySelectorAll('.reply-btn').forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      if (!window.isAuthenticated) {
        window.location.href = "/auth/login";
        return;
      }

      const commentId = this.getAttribute('data-comment-id');
      const commentCard = this.closest('.comment-card');
      
      if (!commentCard) {
        console.error('Parent comment card not found');
        return;
      }

      const commentContent = commentCard.querySelector('.comment-content');
      if (!commentContent) {
        console.error('Comment content not found');
        return;
      }

      currentCommentId = commentId;
      const parentComment = replyModal.querySelector('.parent-comment');
      if (parentComment) {
        parentComment.innerHTML = escapeHTML(commentContent.textContent);
      }

      modal.show();
    });
  });

  // Handle character count
  const replyTextarea = replyModal.querySelector('.reply-textarea');
  const charCount = replyModal.querySelector('.reply-char-count');
  
  if (replyTextarea && charCount) {
    replyTextarea.addEventListener('input', function() {
      const remaining = 200 - this.value.length;
      charCount.textContent = remaining;
      charCount.classList.toggle('text-danger', remaining < 20);
    });
  }

  // Handle reply submission
  const submitButton = replyModal.querySelector('.submit-reply');
  if (submitButton) {
    submitButton.addEventListener('click', function() {
      if (!currentCommentId) {
        console.error('No comment ID found for reply');
        return;
      }

      const replyText = replyTextarea.value.trim();
      if (!replyText) {
        showToast('Reply cannot be empty', 'warning');
        return;
      }

      const originalText = this.innerHTML;
      this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Posting...';
      this.disabled = true;

      fetch('/api/reply_comment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.csrfToken
        },
        body: JSON.stringify({
          parent_comment_id: currentCommentId,
          reply: replyText
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          appendReplyToDOM(currentCommentId, data.reply);
          showToast(data.message, 'success');
          modal.hide();
          replyTextarea.value = '';
          charCount.textContent = '200';
        } else {
          showToast(data.message, 'danger');
        }
      })
      .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred while posting your reply', 'danger');
      })
      .finally(() => {
        this.innerHTML = originalText;
        this.disabled = false;
      });
    });
  }
}

/**
 * Appends the new reply to the DOM without reloading the page.
 * @param {number} parentId - The ID of the parent comment.
 * @param {Object} reply - The reply data returned from the backend.
 */
function appendReplyToDOM(parentId, reply) {
  const commentCard = document.getElementById(`comment-${parentId}`);
  if (!commentCard) return;

  let repliesContainer = commentCard.querySelector(".comment-replies");
  if (!repliesContainer) {
    repliesContainer = document.createElement("div");
    repliesContainer.className = "comment-replies";
    commentCard.appendChild(repliesContainer);
  }

  if (repliesContainer.children.length >= 2) {
    const seeMoreReplies = commentCard.querySelector(".see-more-replies");
    if (!seeMoreReplies) {
      const seeMoreButton = document.createElement("button");
      seeMoreButton.className = "see-more-replies btn btn-link";
      seeMoreButton.textContent = "See more replies";
      seeMoreButton.addEventListener("click", () => {
        Array.from(repliesContainer.children).forEach(child => child.style.display = 'block');
        seeMoreButton.style.display = 'none';
      });
      commentCard.appendChild(seeMoreButton);
    }
  }

  const replyCard = document.createElement("div");
  replyCard.className = "reply-card mb-3 fade-in";
  replyCard.style.display = repliesContainer.children.length >= 2 ? 'none' : 'block';
  replyCard.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-2">
      <div class="d-flex align-items-center">
        <div class="user-avatar me-2">
          <i class="fas fa-user-circle fa-2x text-primary"></i>
        </div>
        <div>
          <h6 class="mb-0">${escapeHTML(reply.username)}</h6>
          <small class="text-muted">${escapeHTML(reply.date_posted)}</small>
        </div>
      </div>
    </div>
    <div class="comment-content mb-3">
      <p class="mb-0">${escapeHTML(reply.content)}</p>
    </div>
  `;
  repliesContainer.appendChild(replyCard);
}

function updateReplyCount(commentId, newCount) {
  const replyButton = document.querySelector(`.reply-btn[data-comment-id='${commentId}']`);
  if (replyButton) {
    replyButton.innerHTML = `<i class="fas fa-reply me-1"></i> Reply (${newCount})`;
  }
}


/**
 * Escapes HTML to prevent XSS attacks when inserting user-generated content.
 * @param {string} str - The string to escape.
 * @returns {string} - The escaped string.
 */
function escapeHTML(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

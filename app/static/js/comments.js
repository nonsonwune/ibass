// app/static/js/comments.js

document.addEventListener("DOMContentLoaded", function () {
  // First initialize systems
  initializeCommentSystem();
  initializeVoting();
  initializeTooltips();

  if (window.isAuthenticated) {
    fetchUserVotes();
  }

  // Then set up replies
  initializeReplySystem();
  
  // Finally, update counts and sort
  setTimeout(() => {
    updateAllReplyCountsOnLoad();
    sortComments();
  }, 100);
});
/**
 * Updates reply counts for all comments on initial page load
 */
function updateAllReplyCountsOnLoad() {
  document.querySelectorAll(".comment-card").forEach((commentCard) => {
    const commentId = commentCard.id.replace("comment-", "");
    const repliesContainer = commentCard.querySelector(".comment-replies");
    if (repliesContainer) {
      const replyCount = repliesContainer.querySelectorAll(".reply-card").length;
      updateReplyCount(commentId, replyCount);
      console.log(`Updated reply count for comment ${commentId}: ${replyCount}`); // Debug line
    }
  });
}

/**
 * Sorts comments by date in descending order (newest first)
 */
function sortComments() {
  const commentList = document.querySelector(".comment-list");
  if (!commentList) return;

  const comments = Array.from(commentList.querySelectorAll(".comment-card"));
  comments.sort((a, b) => {
    const dateA = new Date(a.querySelector(".text-muted").textContent);
    const dateB = new Date(b.querySelector(".text-muted").textContent);
    return dateB - dateA;
  });

  comments.forEach((comment) => {
    commentList.appendChild(comment);
  });
}

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
 * Updates the reply count display on the reply button
 * @param {string} commentId - The ID of the comment
 * @param {number} newCount - The new reply count
 */
function updateReplyCount(commentId, newCount) {
  const replyButton = document.querySelector(
    `.reply-btn[data-comment-id='${commentId}']`
  );
  if (replyButton) {
    replyButton.innerHTML = `
      <i class="fas fa-reply me-1"></i>Reply (${newCount})
    `;
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

  const commentElement = buttonElement.closest(".comment-card, .reply-card");
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

  if (typeof data.user_id === "number" && typeof data.user_score === "number") {
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
 * Initialize the reply button functionality for a comment or reply card
 * @param {HTMLElement} card - The card element to initialize the reply button for
 * @param {number} parentLevel - The nesting level of the parent
 */
function initializeReplyButtonForCard(card, parentLevel) {
  const replyButton = card.querySelector(".reply-btn");
  if (replyButton) {
    replyButton.addEventListener("click", function (e) {
      e.preventDefault();
      if (!window.isAuthenticated) {
        window.location.href = "/auth/login";
        return;
      }

      const commentId = this.getAttribute("data-comment-id");
      const currentParentLevel = parseInt(
        this.getAttribute("data-parent-level") || "0"
      );

      if (currentParentLevel >= 3) {
        showToast("Maximum reply depth reached", "warning");
        return;
      }

      const contentElement = card.querySelector(
        ".comment-content, .reply-content"
      );
      if (!contentElement) {
        console.error("Content element not found");
        return;
      }

      const replyModal = document.getElementById("replyModal");
      if (!replyModal) {
        console.error("Reply modal not found");
        return;
      }

      const modal = new bootstrap.Modal(replyModal);
      const parentComment = replyModal.querySelector(".parent-comment");

      if (parentComment) {
        parentComment.innerHTML = escapeHTML(contentElement.textContent.trim());
      }

      const submitButton = replyModal.querySelector(".submit-reply");
      submitButton.setAttribute("data-parent-id", commentId);
      submitButton.setAttribute("data-parent-level", currentParentLevel);

      modal.show();
    });
  }
}

/**
 * Initializes the reply system by setting up event listeners for reply buttons and reply submissions.
 */
function initializeReplySystem() {
  const replyModal = document.getElementById("replyModal");

  if (!replyModal) {
    console.error("Reply modal not found in DOM");
    return;
  }

  const modal = new bootstrap.Modal(replyModal);
  let currentCommentId = null;
  let currentParentLevel = 0;

  // Handle reply button clicks
  document.querySelectorAll(".reply-btn").forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      if (!window.isAuthenticated) {
        window.location.href = "/auth/login";
        return;
      }

      const commentId = this.getAttribute("data-comment-id");
      const parentLevel = parseInt(
        this.getAttribute("data-parent-level") || "0"
      );

      if (parentLevel >= 3) {
        showToast("Maximum reply depth reached", "warning");
        return;
      }

      const commentCard = this.closest(".comment-card, .reply-card");
      if (!commentCard) {
        console.error("Parent comment/reply card not found");
        return;
      }

      const contentElement = commentCard.querySelector(
        ".comment-content, .reply-content"
      );
      if (!contentElement) {
        console.error("Content element not found");
        return;
      }

      currentCommentId = commentId;
      currentParentLevel = parentLevel;

      const parentComment = replyModal.querySelector(".parent-comment");
      if (parentComment) {
        parentComment.innerHTML = escapeHTML(contentElement.textContent.trim());
      }

      modal.show();
    });
  });

  // Handle character count for replies
  const replyTextarea = replyModal.querySelector(".reply-textarea");
  const charCount = replyModal.querySelector(".reply-char-count");

  if (replyTextarea && charCount) {
    replyTextarea.addEventListener("input", function () {
      const remaining = 200 - this.value.length;
      charCount.textContent = remaining;
      charCount.classList.toggle("text-danger", remaining < 20);
    });
  }

  // Handle reply submission
  const submitButton = replyModal.querySelector(".submit-reply");
  if (submitButton) {
    submitButton.addEventListener("click", handleReplySubmission);
  }
}

/**
 * Handles the submission of a reply
 */
function handleReplySubmission() {
  const replyModal = document.getElementById("replyModal");
  const replyTextarea = replyModal.querySelector(".reply-textarea");
  const currentCommentId = this.getAttribute("data-parent-id");
  const currentParentLevel = parseInt(
    this.getAttribute("data-parent-level") || "0"
  );

  console.log("Submitting reply for comment ID:", currentCommentId); // Log comment ID
  console.log("Reply text:", replyTextarea.value.trim()); // Log reply text

  if (!currentCommentId) {
    console.error("No comment ID found for reply");
    return;
  }

  const replyText = replyTextarea.value.trim();
  if (!replyText) {
    showToast("Reply cannot be empty", "warning");
    return;
  }

  const originalText = this.innerHTML;
  this.innerHTML =
    '<span class="spinner-border spinner-border-sm me-1"></span>Posting...';
  this.disabled = true;

  submitReplyToServer(
    currentCommentId,
    replyText,
    currentParentLevel,
    this,
    originalText
  );
}

/**
 * Submits the reply to the server
 * @param {string} commentId - The ID of the parent comment
 * @param {string} replyText - The reply content
 * @param {number} parentLevel - The nesting level of the parent
 * @param {HTMLElement} submitButton - The submit button element
 * @param {string} originalButtonText - The original button text
 */
function submitReplyToServer(
  commentId,
  replyText,
  parentLevel,
  submitButton,
  originalButtonText
) {
  console.log("Sending reply to server:", { commentId, replyText, parentLevel }); // Log data being sent

  fetch("/api/reply_comment", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": window.csrfToken,
    },
    body: JSON.stringify({
      parent_comment_id: commentId,
      reply: replyText,
      parent_level: parentLevel,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("Server response:", data); // Log server response
      if (data.success) {
        appendReplyToDOM(commentId, data.reply, parentLevel);
        showToast(data.message, "success");
        resetReplyModal();
      } else {
        showToast(data.message, "danger");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showToast("An error occurred while posting your reply", "danger");
    })
    .finally(() => {
      submitButton.innerHTML = originalButtonText;
      submitButton.disabled = false;
    });
}

/**
 * Resets the reply modal to its initial state
 */
function resetReplyModal() {
  const replyModal = document.getElementById("replyModal");
  const modal = bootstrap.Modal.getInstance(replyModal);
  const replyTextarea = replyModal.querySelector(".reply-textarea");
  const charCount = replyModal.querySelector(".reply-char-count");

  modal.hide();
  replyTextarea.value = "";
  charCount.textContent = "200";
}

/**
 * Appends the new reply to the DOM without reloading the page.
 * @param {number} parentId - The ID of the parent comment/reply.
 * @param {Object} reply - The reply data returned from the backend.
 * @param {number} parentLevel - The nesting level of the parent.
 */
function appendReplyToDOM(parentId, reply, parentLevel) {
  const parentElement = document.getElementById(`comment-${parentId}`);
  if (!parentElement) {
    console.error(`Parent element not found for ID ${parentId}`);
    return;
  }

  let repliesContainer = parentElement.querySelector(".comment-replies");
  if (!repliesContainer) {
    repliesContainer = document.createElement("div");
    repliesContainer.className = "comment-replies mt-3";
    repliesContainer.id = `replies-${parentId}`;
    parentElement.appendChild(repliesContainer);
  }

  const replyCard = createReplyCard(reply, parentLevel);
  repliesContainer.appendChild(replyCard);

  // Update reply count
  const replyCount = repliesContainer.querySelectorAll(".reply-card").length;
  updateReplyCount(parentId, replyCount);

  // Initialize interactive elements
  initializeVoting();
  initializeTooltips();
  initializeReplyButtonForCard(replyCard, parentLevel);

  // Scroll the new reply into view smoothly
  replyCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/**
 * Creates a reply card element
 * @param {Object} reply - The reply data
 * @param {number} parentLevel - The nesting level of the parent
 * @returns {HTMLElement} The created reply card element
 */
function createReplyCard(reply, parentLevel) {
  const replyCard = document.createElement("div");
  replyCard.className = "reply-card animate__animated animate__fadeIn";
  replyCard.id = `comment-${reply.id}`;

  replyCard.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-2">
      <div class="d-flex align-items-center">
        <div class="user-avatar me-2">
          <i class="fas fa-user-circle text-primary"></i>
        </div>
        <div>
          <h6 class="mb-0 ${reply.is_admin ? "admin-username" : ""}">
            ${escapeHTML(reply.username)}
            <span class="badge bg-primary-soft ms-1 user-score" data-user-id="${
              reply.user_id
            }">
              ${reply.score || 0}
            </span>
          </h6>
          <small class="text-muted">${escapeHTML(reply.date_posted)}</small>
        </div>
      </div>
    </div>
    <div class="reply-content mb-2">
      <p class="mb-0">${escapeHTML(reply.content)}</p>
    </div>
    <div class="d-flex justify-content-between align-items-center">
      <div class="btn-group btn-group-sm">
        <button class="btn btn-sm btn-outline-primary vote-btn"
                data-comment-id="${reply.id}"
                data-vote-type="like">
          <i class="fas fa-thumbs-up me-1"></i>
          <span class="like-count">(${reply.likes || 0})</span>
        </button>
        <button class="btn btn-sm btn-outline-danger vote-btn"
                data-comment-id="${reply.id}"
                data-vote-type="dislike">
          <i class="fas fa-thumbs-down me-1"></i>
          <span class="dislike-count">(${reply.dislikes || 0})</span>
        </button>
        <button class="btn btn-sm btn-outline-secondary reply-btn"
                data-comment-id="${reply.id}"
                data-parent-level="${parentLevel + 1}">
          <i class="fas fa-reply me-1"></i>Reply
        </button>
      </div>
      ${getDeleteButtonHTML(reply)}
    </div>
  `;

  return replyCard;
}

/**
 * Gets the HTML for the delete button if the user has permission
 * @param {Object} reply - The reply data
 * @returns {string} The delete button HTML or empty string
 */
function getDeleteButtonHTML(reply) {
  if (
    window.isAuthenticated &&
    (reply.user_id === window.currentUserId || window.isAdmin)
  ) {
    return `
      <div class="reply-actions">
        <form action="/delete_comment/${reply.id}" method="POST" class="d-inline delete-comment-form">
          <input type="hidden" name="csrf_token" value="${window.csrfToken}">
          <button type="submit"
                  class="btn btn-sm btn-danger"
                  data-bs-toggle="tooltip"
                  data-bs-placement="top"
                  title="Delete reply">
            <i class="fas fa-trash-alt"></i>
          </button>
        </form>
      </div>
    `;
  }
  return "";
}

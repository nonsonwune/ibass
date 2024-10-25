// app/static/js/scripts.js

// Main initialization
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM fully loaded in scripts.js");
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

// Tooltip initialization
function initializeTooltips() {
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });
}

// Comment System
function initializeCommentSystem() {
  const commentTextarea = document.getElementById("comment");
  const charCount = document.getElementById("charCount");

  if (commentTextarea && charCount) {
    commentTextarea.addEventListener("input", function () {
      const remaining = 200 - this.value.length;
      charCount.textContent = `${remaining} characters remaining`;
      charCount.classList.toggle("text-danger", remaining < 20);
    });
  }
}

// Voting System
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

// Keep track of ongoing vote requests
const pendingVotes = new Set();

function vote(commentId, action, buttonElement) {
  const voteKey = `${commentId}-${action}`;

  if (pendingVotes.has(voteKey) || buttonElement.disabled) {
    return;
  }

  const commentElement = buttonElement.closest(".list-group-item");
  if (!commentElement) {
    showToast("Error finding comment element", "danger");
    return;
  }

  // Cache elements and original state
  const buttons = {
    like: commentElement.querySelector('[data-vote-type="like"]'),
    dislike: commentElement.querySelector('[data-vote-type="dislike"]'),
  };

  const originalState = {
    like: {
      content: buttons.like.innerHTML,
      disabled: buttons.like.disabled,
    },
    dislike: {
      content: buttons.dislike.innerHTML,
      disabled: buttons.dislike.disabled,
    },
  };

  // Show loading state
  const loadingSpinner =
    '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>';
  buttons[action].innerHTML =
    loadingSpinner + (action === "like" ? "Liking..." : "Disliking...");
  Object.values(buttons).forEach((btn) => (btn.disabled = true));

  pendingVotes.add(voteKey);

  // Set timeout to prevent UI from being stuck
  const timeout = setTimeout(() => {
    resetVoteButtonState();
    showToast("Vote request timed out. Please try again.", "warning");
  }, 5000);

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
      clearTimeout(timeout);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || response.statusText);
      return data;
    })
    .then((data) => {
      if (!data.success)
        throw new Error(data.message || "Vote processing failed");
      updateVoteUI(commentElement, data);
      showToast("Vote recorded successfully", "success");
    })
    .catch((error) => {
      console.error("Vote error:", error);
      showToast(error.message || "Error processing vote", "danger");
    })
    .finally(() => {
      resetVoteButtonState();
      pendingVotes.delete(voteKey);
      fetchUserVotes();
    });

  function resetVoteButtonState() {
    // Restore original button states
    Object.entries(buttons).forEach(([type, button]) => {
      button.innerHTML = originalState[type].content;
      button.disabled = originalState[type].disabled;
    });
  }
}

function updateVoteUI(commentElement, data) {
  // Get all relevant elements
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

  // Update all instances of this user's score
  if (typeof data.user_id === "number" && typeof data.user_score === "number") {
    document
      .querySelectorAll(`.user-score[data-user-id="${data.user_id}"]`)
      .forEach((el) => (el.textContent = data.user_score));
  }
}

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

// Bookmark System
function initializeBookmarkSystem() {
  console.log("Initializing bookmark system");
  const bookmarkButtons = document.querySelectorAll(".bookmark-btn");

  bookmarkButtons.forEach((button) => {
    button.addEventListener("click", handleBookmarkClick);
  });
}

function handleBookmarkClick(event) {
  event.preventDefault();

  if (!window.isAuthenticated) {
    window.location.href = "/auth/login";
    return;
  }

  const button = this;
  const uniId = button.getAttribute("data-uni-id");
  const isBookmarked = button.classList.contains("btn-secondary");

  const url = isBookmarked ? `/api/remove_bookmark/${uniId}` : "/api/bookmark";
  const method = "POST";
  const body = isBookmarked ? null : JSON.stringify({ university_id: uniId });

  fetch(url, {
    method: method,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": window.csrfToken,
    },
    body: body,
  })
    .then((response) => {
      if (response.redirected || response.status === 401) {
        throw new Error("Please sign in to bookmark institutions.");
      }
      if (!response.ok) {
        throw new Error("An unexpected error occurred.");
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        updateBookmarkButtonUI(button, !isBookmarked);
        showToast(
          isBookmarked ? "Bookmark removed" : "Institution bookmarked",
          "success"
        );
      } else {
        throw new Error(data.message || "Bookmarking failed");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showToast(
        error.message || "An error occurred while bookmarking",
        "danger"
      );
    });
}

function fetchUserBookmarks() {
  fetch("/api/user_bookmarks", {
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
        applyUserBookmarks(data);
      }
    })
    .catch((error) => {
      console.error("Error fetching user bookmarks:", error);
    });
}

function applyUserBookmarks(bookmarks) {
  document.querySelectorAll(".bookmark-btn").forEach((button) => {
    const uniId = button.getAttribute("data-uni-id");
    updateBookmarkButtonUI(button, bookmarks.includes(parseInt(uniId)));
  });
}

function updateBookmarkButtonUI(button, isBookmarked) {
  const bookmarkText = button.querySelector(".bookmark-text");
  const icon = button.querySelector("i");

  if (isBookmarked) {
    button.classList.add("btn-secondary");
    button.classList.remove("btn-outline-secondary");
    bookmarkText.textContent = "Bookmarked";
    icon.classList.remove("fa-bookmark");
    icon.classList.add("fa-check");
  } else {
    button.classList.remove("btn-secondary");
    button.classList.add("btn-outline-secondary");
    bookmarkText.textContent = "Bookmark";
    icon.classList.add("fa-bookmark");
    icon.classList.remove("fa-check");
  }
}

// Institution Modal
function initializeInstitutionModal() {
  console.log("Initializing institution modal");
  const institutionModal = document.getElementById("institutionModal");
  if (!institutionModal) return;

  institutionModal.addEventListener("show.bs.modal", function (event) {
    const button = event.relatedTarget;
    const uniId = button.getAttribute("data-uni-id");
    const selectedCourse = button.getAttribute("data-selected-course");
    resetModal();

    if (uniId) {
      fetchInstitutionDetails(uniId, selectedCourse);
    } else {
      showModalError("Unable to retrieve institution details.");
    }
  });

  institutionModal.addEventListener("shown.bs.modal", function () {
    setupCourseSearch();
  });
}

function resetModal() {
  const elements = {
    institutionDetails: document.getElementById("institutionDetails"),
    modalErrorMessage: document.getElementById("modalErrorMessage"),
    loadingIndicator: document.getElementById("loadingIndicator"),
    institutionName: document.getElementById("institutionName"),
    institutionState: document.getElementById("institutionState"),
    institutionProgramType: document.getElementById("institutionProgramType"),
    institutionWebsite: document.getElementById("institutionWebsite"),
    institutionEstablished: document.getElementById("institutionEstablished"),
    coursesList: document.getElementById("coursesList"),
  };

  elements.institutionDetails.style.display = "none";
  elements.modalErrorMessage.style.display = "none";
  elements.loadingIndicator.style.display = "block";

  Object.keys(elements).forEach((key) => {
    if (elements[key] && typeof elements[key].textContent !== "undefined") {
      elements[key].textContent = "";
    }
  });
}

function fetchInstitutionDetails(uniId, selectedCourse) {
  const url = selectedCourse
    ? `/api/institution/${uniId}?selected_course=${encodeURIComponent(
        selectedCourse
      )}`
    : `/api/institution/${uniId}`;

  fetch(url)
    .then((response) => {
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      return response.json();
    })
    .then((data) => {
      if (selectedCourse) {
        data.selected_course = selectedCourse;
      }
      populateModal(data);
    })
    .catch((error) => {
      console.error("Error fetching institution details:", error);
      showModalError("Error loading institution details. Please try again.");
    });
}

function populateModal(data) {
  const elements = {
    institutionName: document.getElementById("institutionName"),
    institutionState: document.getElementById("institutionState"),
    institutionProgramType: document.getElementById("institutionProgramType"),
    institutionWebsite: document.getElementById("institutionWebsite"),
    institutionEstablished: document.getElementById("institutionEstablished"),
    coursesList: document.getElementById("coursesList"),
    loadingIndicator: document.getElementById("loadingIndicator"),
    institutionDetails: document.getElementById("institutionDetails"),
  };

  // Populate basic info
  elements.institutionName.textContent = data.university_name;
  elements.institutionState.textContent = data.state;
  elements.institutionProgramType.textContent = data.program_type;
  elements.institutionWebsite.innerHTML = data.website
    ? `<a href="${data.website}" target="_blank" rel="noopener noreferrer">${data.website}</a>`
    : "Not Available";
  elements.institutionEstablished.textContent =
    data.established || "Not Available";

  // Populate courses
  if (data.courses?.length > 0) {
    elements.coursesList.innerHTML = data.courses
      .map((course, index) =>
        createCourseHTML(course, data.selected_course, index)
      )
      .join("");
  } else {
    elements.coursesList.innerHTML =
      '<p class="text-muted">No courses available for this institution.</p>';
  }

  // Show details
  elements.loadingIndicator.style.display = "none";
  elements.institutionDetails.style.display = "block";

  // Setup course search if needed
  setupCourseSearch();
}

function createCourseHTML(course, selectedCourse, index) {
  const isSelected =
    selectedCourse &&
    course.course_name.toLowerCase() === selectedCourse.toLowerCase();

  return `
    <div class="accordion-item ${isSelected ? "selected-course" : ""}">
      <h2 class="accordion-header">
        <button class="accordion-button ${!isSelected ? "collapsed" : ""}" 
                type="button" 
                data-bs-toggle="collapse" 
                data-bs-target="#course-${index}"
                aria-expanded="${isSelected}"
                aria-controls="course-${index}">
          ${course.course_name}
          ${
            course.abbrv
              ? `<span class="ms-2 badge bg-secondary">${course.abbrv}</span>`
              : ""
          }
          ${
            isSelected
              ? '<span class="ms-2 badge bg-success">Selected Course</span>'
              : ""
          }
        </button>
      </h2>
      <div id="course-${index}" 
           class="accordion-collapse collapse ${isSelected ? "show" : ""}"
           aria-expanded="${isSelected}">
        <div class="accordion-body">
          <div class="course-details">
            <div class="mb-3">
              <h6 class="text-primary mb-2">UTME Requirements</h6>
              <p class="mb-0">${course.utme_requirements || "Not specified"}</p>
            </div>
            <div class="mb-3">
              <h6 class="text-primary mb-2">Direct Entry Requirements</h6>
              <p class="mb-0">${
                course.direct_entry_requirements || "Not specified"
              }</p>
            </div>
            <div>
              <h6 class="text-primary mb-2">Required Subjects</h6>
              <p class="mb-0">${course.subjects || "Not specified"}</p>
            </div>
          </div>
      </div>
    </div>
  `;
}

function setupCourseSearch() {
  const searchInput = document.getElementById("courseSearch");
  if (!searchInput) return;

  searchInput.value = "";
  searchInput.removeEventListener("input", handleCourseSearch);
  searchInput.addEventListener("input", handleCourseSearch);
}

function handleCourseSearch(event) {
  const searchTerm = event.target.value.toLowerCase();
  const accordionItems = document.querySelectorAll(
    "#coursesList .accordion-item"
  );
  let visibleCount = 0;

  accordionItems.forEach((item) => {
    const courseName = item
      .querySelector(".accordion-button")
      .textContent.toLowerCase();
    const isVisible = courseName.includes(searchTerm);
    item.style.display = isVisible ? "block" : "none";
    if (isVisible) visibleCount++;
  });

  updateNoResultsMessage(visibleCount);
}

function updateNoResultsMessage(visibleCount) {
  const existingMessage = document.getElementById("noCoursesFound");
  if (visibleCount === 0) {
    if (!existingMessage) {
      const message = document.createElement("div");
      message.id = "noCoursesFound";
      message.className = "alert alert-info mt-3";
      message.textContent = "No courses found matching your search.";
      document.getElementById("coursesList").appendChild(message);
    }
  } else if (existingMessage) {
    existingMessage.remove();
  }
}

function showModalError(message) {
  const errorDiv = document.getElementById("modalErrorMessage");
  const loadingIndicator = document.getElementById("loadingIndicator");

  if (errorDiv) {
    errorDiv.textContent = message;
    errorDiv.style.display = "block";
    if (loadingIndicator) {
      loadingIndicator.style.display = "none";
    }
  } else {
    console.error("Error element not found:", message);
  }
}

// Toast Notification System
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

// Utility Functions
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Error Handling
function handleError(error, context = "") {
  console.error(`Error in ${context}:`, error);
  showToast(error.message || "An unexpected error occurred", "danger");
}

// CSRF Token Handling
function getCSRFToken() {
  return (
    document
      .querySelector('meta[name="csrf-token"]')
      ?.getAttribute("content") || window.csrfToken
  );
}

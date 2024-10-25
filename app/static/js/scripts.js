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

  // Show loading state
  const buttons = {
    like: commentElement.querySelector('[data-vote-type="like"]'),
    dislike: commentElement.querySelector('[data-vote-type="dislike"]'),
  };

  const loadingSpinner =
    '<span class="spinner-border spinner-border-sm me-1" role="status"></span>';
  buttons[action].innerHTML =
    loadingSpinner + (action === "like" ? "Liking..." : "Disliking...");
  Object.values(buttons).forEach((btn) => (btn.disabled = true));

  pendingVotes.add(voteKey);

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

      // Update UI
      if (buttons.like && buttons.dislike) {
        // Update counts
        const likeCount = buttons.like.querySelector(".like-count");
        const dislikeCount = buttons.dislike.querySelector(".dislike-count");
        if (likeCount) likeCount.textContent = `(${data.likes})`;
        if (dislikeCount) dislikeCount.textContent = `(${data.dislikes})`;

        // Update active states
        buttons.like.classList.remove("active");
        buttons.dislike.classList.remove("active");
        if (data.user_vote === "like") {
          buttons.like.classList.add("active");
        } else if (data.user_vote === "dislike") {
          buttons.dislike.classList.add("active");
        }
      }

      showToast(data.message || "Vote recorded successfully", "success");
    })
    .catch((error) => {
      console.error("Vote error:", error);
      showToast(error.message || "Error processing vote", "danger");
    })
    .finally(() => {
      // Reset button states
      if (buttons.like && buttons.dislike) {
        buttons.like.innerHTML =
          '<i class="fas fa-thumbs-up"></i> Like <span class="like-count"></span>';
        buttons.dislike.innerHTML =
          '<i class="fas fa-thumbs-down"></i> Dislike <span class="dislike-count"></span>';
        buttons.like.disabled = false;
        buttons.dislike.disabled = false;
      }
      pendingVotes.delete(voteKey);
      fetchUserVotes(); // Refresh vote states
    });
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
  if (!institutionModal) {
    console.error("Modal element not found");
    return;
  }

  // Create a Bootstrap modal instance
  const modal = new bootstrap.Modal(institutionModal);

  institutionModal.addEventListener("show.bs.modal", function (event) {
    console.log("Modal show event triggered");
    // Reset modal state and show loading
    resetModal();

    const button = event.relatedTarget;
    if (!button) {
      showModalError("Invalid trigger element");
      return;
    }

    const uniId = button.getAttribute("data-uni-id");
    const selectedCourse = button.getAttribute("data-selected-course");

    if (!uniId) {
      showModalError("Invalid institution ID");
      return;
    }

    // Store data for use after modal is shown
    institutionModal.dataset.pendingUniId = uniId;
    institutionModal.dataset.pendingSelectedCourse = selectedCourse;
  });

  institutionModal.addEventListener("shown.bs.modal", function () {
    console.log("Modal shown event triggered");
    const uniId = institutionModal.dataset.pendingUniId;
    const selectedCourse = institutionModal.dataset.pendingSelectedCourse;

    if (uniId) {
      fetchInstitutionDetails(uniId, selectedCourse);
    }

    // Clean up stored data
    delete institutionModal.dataset.pendingUniId;
    delete institutionModal.dataset.pendingSelectedCourse;

    setupCourseSearch();
  });
}

function resetModal() {
  const modalBody = document.querySelector("#institutionModal .modal-body");
  if (!modalBody) {
    console.error("Modal body not found");
    return;
  }

  // Reset by recreating the entire modal content structure
  modalBody.innerHTML = `
      <div id="loadingIndicator" class="text-center py-4">
          <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
          </div>
          <p class="mt-2">Loading institution details...</p>
      </div>
      <div id="modalErrorMessage" class="alert alert-danger" style="display: none"></div>
      <div id="institutionDetails" style="display: none">
          <div class="row">
              <div class="col-12">
                  <h3 id="institutionName" class="mb-4"></h3>
                  <div class="institution-info">
                      <div class="row g-3">
                          <div class="col-md-6">
                              <div class="d-flex align-items-center">
                                  <i class="fas fa-map-marker-alt me-2 text-primary"></i>
                                  <div>
                                      <strong>State:</strong>
                                      <span id="institutionState" class="ms-2"></span>
                                  </div>
                              </div>
                          </div>
                          <div class="col-md-6">
                              <div class="d-flex align-items-center">
                                  <i class="fas fa-graduation-cap me-2 text-primary"></i>
                                  <div>
                                      <strong>Program Type:</strong>
                                      <span id="institutionProgramType" class="ms-2"></span>
                                  </div>
                              </div>
                          </div>
                          <div class="col-md-6">
                              <div class="d-flex align-items-center">
                                  <i class="fas fa-globe me-2 text-primary"></i>
                                  <div>
                                      <strong>Website:</strong>
                                      <span id="institutionWebsite" class="ms-2"></span>
                                  </div>
                              </div>
                          </div>
                          <div class="col-md-6">
                              <div class="d-flex align-items-center">
                                  <i class="fas fa-calendar-alt me-2 text-primary"></i>
                                  <div>
                                      <strong>Established:</strong>
                                      <span id="institutionEstablished" class="ms-2"></span>
                                  </div>
                              </div>
                          </div>
                      </div>
                  </div>
              </div>
          </div>
          <div class="courses-section mt-4">
              <ul class="nav nav-tabs" id="institutionTab" role="tablist">
                  <li class="nav-item" role="presentation">
                      <button class="nav-link active" id="courses-tab" data-bs-toggle="tab" data-bs-target="#courses" type="button" role="tab">
                          <i class="fas fa-list me-1"></i> All Available Courses
                      </button>
                  </li>
              </ul>
              <div class="tab-content p-3 border border-top-0 rounded-bottom" id="institutionTabContent">
                  <div class="tab-pane fade show active" id="courses" role="tabpanel">
                      <div class="mb-3">
                          <input type="text" class="form-control" id="courseSearch" placeholder="Search courses...">
                      </div>
                      <div id="coursesList" class="accordion"></div>
                  </div>
              </div>
          </div>
      </div>
  `;
}

function fetchInstitutionDetails(uniId, selectedCourse) {
  const url = selectedCourse
    ? `/api/institution/${uniId}?selected_course=${encodeURIComponent(
        selectedCourse
      )}`
    : `/api/institution/${uniId}`;

  fetch(url)
    .then(async (response) => {
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.error || `HTTP error! status: ${response.status}`
        );
      }
      return response.json();
    })
    .then((data) => {
      if (!data) {
        throw new Error("No data received from server");
      }
      console.log("Received institution data:", data); // Debug log
      if (selectedCourse) {
        data.selected_course = selectedCourse;
      }
      populateModal(data);
    })
    .catch((error) => {
      console.error("Error fetching institution details:", error);
      showModalError(
        error.message || "Error loading institution details. Please try again."
      );
    });
}

function populateModal(data) {
  try {
    const elements = {
      institutionName: document.getElementById("institutionName"),
      institutionState: document.getElementById("institutionState"),
      institutionProgramType: document.getElementById("institutionProgramType"),
      institutionWebsite: document.getElementById("institutionWebsite"),
      institutionEstablished: document.getElementById("institutionEstablished"),
      coursesList: document.getElementById("coursesList"),
      loadingIndicator: document.getElementById("loadingIndicator"),
      institutionDetails: document.getElementById("institutionDetails"),
      modalErrorMessage: document.getElementById("modalErrorMessage"),
    };

    // Verify all required elements exist
    Object.entries(elements).forEach(([key, element]) => {
      if (!element) {
        throw new Error(`Required element ${key} not found in DOM`);
      }
    });

    // Hide error message if it was previously shown
    elements.modalErrorMessage.style.display = "none";

    // Populate basic info
    elements.institutionName.textContent = data.university_name || "N/A";
    elements.institutionState.textContent = data.state || "N/A";
    elements.institutionProgramType.textContent = data.program_type || "N/A";
    elements.institutionWebsite.innerHTML = data.website
      ? `<a href="${data.website}" target="_blank" rel="noopener noreferrer">${data.website}</a>`
      : "Not Available";
    elements.institutionEstablished.textContent =
      data.established || "Not Available";

    // Populate courses
    if (Array.isArray(data.courses) && data.courses.length > 0) {
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

    // Setup course search
    setupCourseSearch();

    console.log("Modal populated successfully"); // Debug log
  } catch (error) {
    console.error("Error in populateModal:", error);
    showModalError(`Error displaying institution details: ${error.message}`);
  }
}

function showModalError(message) {
  const elements = {
    errorDiv: document.getElementById("modalErrorMessage"),
    loadingIndicator: document.getElementById("loadingIndicator"),
    institutionDetails: document.getElementById("institutionDetails"),
  };

  if (!elements.errorDiv) {
    console.error("Error element not found");
    return;
  }

  // Hide other elements
  if (elements.loadingIndicator) {
    elements.loadingIndicator.style.display = "none";
  }
  if (elements.institutionDetails) {
    elements.institutionDetails.style.display = "none";
  }

  // Show error message
  elements.errorDiv.textContent = message;
  elements.errorDiv.style.display = "block";
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

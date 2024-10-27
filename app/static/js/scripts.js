// app/static/js/scripts.js

// State Management
const AppState = {
  modalState: {
    isLoading: false,
    currentInstitution: null,
    courseSearchTerm: "",
    selectedCourse: null,
  },

  pendingVotes: new Set(),

  setModalLoading(loading) {
    this.modalState.isLoading = loading;
    this.updateModalUI();
  },

  updateModalUI() {
    const loadingIndicator = document.getElementById("loadingIndicator");
    const institutionDetails = document.getElementById("institutionDetails");
    const modalErrorMessage = document.getElementById("modalErrorMessage");

    if (this.modalState.isLoading) {
      loadingIndicator.style.display = "block";
      institutionDetails.style.display = "none";
      modalErrorMessage.style.display = "none";
    } else {
      loadingIndicator.style.display = "none";
      institutionDetails.style.display = "block";
    }
  },
};

// Main initialization
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
      charCount.textContent = `${remaining} remaining`;
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

function vote(commentId, action, buttonElement) {
  const voteKey = `${commentId}-${action}`;

  if (AppState.pendingVotes.has(voteKey) || buttonElement.disabled) {
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

  AppState.pendingVotes.add(voteKey);

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
      AppState.pendingVotes.delete(voteKey);
      fetchUserVotes();
    });
}

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

// Fetch User Votes
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

async function handleBookmarkClick(event) {
  event.preventDefault();

  if (!window.isAuthenticated) {
    window.location.href = "/auth/login";
    return;
  }

  const button = this;
  const uniId = button.getAttribute("data-uni-id");
  const isBookmarked = button.classList.contains("btn-secondary");

  try {
    const url = isBookmarked
      ? `/api/remove_bookmark/${uniId}`
      : "/api/bookmark";
    const method = "POST";
    const body = isBookmarked ? null : JSON.stringify({ university_id: uniId });

    const response = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.csrfToken,
      },
      body,
    });

    if (response.redirected || response.status === 401) {
      throw new Error("Please sign in to bookmark institutions.");
    }

    if (!response.ok) {
      throw new Error("An unexpected error occurred.");
    }

    const data = await response.json();

    if (data.success) {
      updateBookmarkButtonUI(button, !isBookmarked);
      showToast(
        isBookmarked ? "Bookmark removed" : "Institution bookmarked",
        "success"
      );
    } else {
      throw new Error(data.message || "Bookmarking failed");
    }
  } catch (error) {
    console.error("Bookmark error:", error);
    showToast(error.message || "Error managing bookmark", "danger");
  }
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

// Institution Modal System
function initializeInstitutionModal() {
  console.log("Initializing institution modal");
  const modal = document.getElementById("institutionModal");
  if (!modal) {
    console.warn("Modal element not found");
    return;
  }

  const bootstrapModal = new bootstrap.Modal(modal);

  modal.addEventListener("show.bs.modal", handleModalShow);
  modal.addEventListener("shown.bs.modal", handleModalShown);
  modal.addEventListener("hidden.bs.modal", handleModalHidden);

  modal.addEventListener("shown.bs.modal", () => {
    const searchInput = document.getElementById("courseSearch");
    if (searchInput) {
      searchInput.focus();
    }
  });
}

function handleModalShow(event) {
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

  AppState.modalState.currentInstitution = { id: uniId, selectedCourse };
  resetModal();
}

function handleModalShown() {
  if (AppState.modalState.currentInstitution) {
    fetchInstitutionDetails(
      AppState.modalState.currentInstitution.id,
      AppState.modalState.currentInstitution.selectedCourse
    );
  }
}

function handleModalHidden() {
  AppState.modalState = {
    isLoading: false,
    currentInstitution: null,
    courseSearchTerm: "",
    selectedCourse: null,
  };
  resetModal();
}

function resetModal() {
  const modalBody = document.querySelector("#institutionModal .modal-body");
  if (!modalBody) {
    console.error("Modal body not found");
    return;
  }

  modalBody.innerHTML = `
      <div id="loadingIndicator" class="text-center py-4">
          <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
          </div>
          <p class="mt-2">Loading institution details...</p>
      </div>
      <div id="modalErrorMessage" class="alert alert-danger" style="display: none"></div>
      <div id="institutionDetails" style="display: none">
          <!-- Institution details will be populated here -->
      </div>
  `;
}

// Institution Details Fetching
async function fetchInstitutionDetails(uniId, selectedCourse) {
  AppState.setModalLoading(true);

  try {
    const url = selectedCourse
      ? `/api/institution/${uniId}?selected_course=${encodeURIComponent(
          selectedCourse
        )}`
      : `/api/institution/${uniId}`;

    const response = await fetch(url);

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.error || `HTTP error! status: ${response.status}`
      );
    }

    const data = await response.json();

    if (!data) {
      throw new Error("No data received from server");
    }

    if (selectedCourse) {
      data.selected_course = selectedCourse;
    }

    populateModal(data);
  } catch (error) {
    console.error("Error fetching institution details:", error);
    showModalError(error.message || "Error loading institution details");
  } finally {
    AppState.setModalLoading(false);
  }
}

function populateModal(data) {
  try {
    const institutionDetails = document.getElementById("institutionDetails");
    if (!institutionDetails) {
      throw new Error("Institution details container not found");
    }

    // Build institution details HTML
    institutionDetails.innerHTML = `
      <div class="row">
        <div class="col-12">
          <h3 id="institutionName" class="mb-4">${
            data.university_name || "N/A"
          }</h3>
          <div class="institution-info">
            <div class="row g-3">
              <div class="col-md-6">
                <div class="d-flex align-items-center">
                  <i class="fas fa-map-marker-alt me-2 text-primary"></i>
                  <div>
                    <strong>State:</strong>
                    <span id="institutionState" class="ms-2">${
                      data.state || "N/A"
                    }</span>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="d-flex align-items-center">
                  <i class="fas fa-graduation-cap me-2 text-primary"></i>
                  <div>
                    <strong>Program Type:</strong>
                    <span id="institutionProgramType" class="ms-2">${
                      data.program_type || "N/A"
                    }</span>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="d-flex align-items-center">
                  <i class="fas fa-globe me-2 text-primary"></i>
                  <div>
                    <strong>Website:</strong>
                    <span id="institutionWebsite" class="ms-2">
                      ${
                        data.website
                          ? `<a href="${data.website}" target="_blank" rel="noopener noreferrer">${data.website}</a>`
                          : "Not Available"
                      }
                    </span>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="d-flex align-items-center">
                  <i class="fas fa-calendar-alt me-2 text-primary"></i>
                  <div>
                    <strong>Established:</strong>
                    <span id="institutionEstablished" class="ms-2">${
                      data.established || "Not Available"
                    }</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Selected Course Section -->
      <div id="selectedCourseSection" class="mt-4" style="display: none">
        <div class="card border-success">
          <div class="card-header bg-success text-white d-flex align-items-center">
            <i class="fas fa-star me-2"></i>
            <h5 class="mb-0">Selected Course</h5>
          </div>
          <div class="card-body" id="selectedCourseDetails"></div>
        </div>
      </div>

      <div class="courses-section mt-4">
        <div class="course-search-header d-flex justify-content-between align-items-center mb-3">
          <h5 class="mb-0">Available Courses</h5>
          <span id="courseCount" class="badge bg-secondary">0 courses</span>
        </div>
        <div class="course-search-wrapper mb-3">
          <input type="text" class="form-control" id="courseSearch" placeholder="Search courses...">
          <i class="fas fa-search search-icon"></i>
        </div>
        <div id="coursesList" class="accordion"></div>
      </div>
    `;

    // Handle selected course if exists
    if (data.selected_course) {
      const selectedCourseData = data.courses.find(
        (course) =>
          course.course_name.toLowerCase() ===
          data.selected_course.toLowerCase()
      );

      if (selectedCourseData) {
        const selectedCourseSection = document.getElementById(
          "selectedCourseSection"
        );
        const selectedCourseDetails = document.getElementById(
          "selectedCourseDetails"
        );

        selectedCourseSection.style.display = "block";
        selectedCourseDetails.innerHTML =
          createCourseDetailsHTML(selectedCourseData);
      }
    }

    // Populate courses list
    if (Array.isArray(data.courses) && data.courses.length > 0) {
      const coursesList = document.getElementById("coursesList");
      coursesList.innerHTML = data.courses
        .map((course, index) =>
          createCourseHTML(course, data.selected_course, index)
        )
        .join("");

      // Update course count
      const totalCourses = data.courses.length;
      const coursesCounter = document.querySelector(
        ".course-search-header .badge"
      );
      if (coursesCounter) {
        coursesCounter.textContent = `${totalCourses} course${
          totalCourses !== 1 ? "s" : ""
        }`;
      }
    } else {
      const coursesList = document.getElementById("coursesList");
      coursesList.innerHTML = `
        <div class="text-center py-4 text-muted">
          <i class="fas fa-info-circle fa-2x mb-2"></i>
          <p class="mb-0">No courses available for this institution.</p>
        </div>
      `;
      const coursesCounter = document.querySelector(
        ".course-search-header .badge"
      );
      if (coursesCounter) {
        coursesCounter.textContent = "0 courses";
      }
    }

    // Initialize course search functionality
    CourseSearch.initialize();
  } catch (error) {
    console.error("Error in populateModal:", error);
    showModalError(`Error displaying institution details: ${error.message}`);
  }
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
          <div class="d-flex align-items-center justify-content-between w-100">
            <span class="me-auto">${course.course_name}</span>
            <div class="badges">
              ${
                course.abbrv
                  ? `<span class="badge bg-secondary me-2">${course.abbrv}</span>`
                  : ""
              }
              ${
                isSelected
                  ? '<span class="badge bg-success">Selected Course</span>'
                  : ""
              }
            </div>
          </div>
        </button>
      </h2>
      <div id="course-${index}" 
           class="accordion-collapse collapse ${isSelected ? "show" : ""}"
           aria-labelledby="heading-${index}">
        <div class="accordion-body">
          <div class="course-details">
            <div class="requirement-section mb-3">
              <h6 class="text-primary d-flex align-items-center mb-2">
                <i class="fas fa-clipboard-list me-2"></i>UTME Requirements
              </h6>
              <div class="ps-4">
                ${course.utme_requirements || "Not specified"}
              </div>
            </div>
            
            <div class="requirement-section mb-3">
              <h6 class="text-primary d-flex align-items-center mb-2">
                <i class="fas fa-door-open me-2"></i>Direct Entry Requirements
              </h6>
              <div class="ps-4">
                ${course.direct_entry_requirements || "Not specified"}
              </div>
            </div>
            
            <div class="requirement-section">
              <h6 class="text-primary d-flex align-items-center mb-2">
                <i class="fas fa-book me-2"></i>Required Subjects
              </h6>
              <div class="ps-4">
                ${course.subjects || "Not specified"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function createCourseDetailsHTML(course) {
  return `
    <div class="selected-course-details">
      <h6 class="mb-3">${course.course_name}</h6>
      <div class="requirement-section mb-3">
        <strong class="d-block mb-2">UTME Requirements:</strong>
        <p class="mb-0">${course.utme_requirements || "Not specified"}</p>
      </div>
      <div class="requirement-section mb-3">
        <strong class="d-block mb-2">Direct Entry Requirements:</strong>
        <p class="mb-0">${
          course.direct_entry_requirements || "Not specified"
        }</p>
      </div>
      <div class="requirement-section">
        <strong class="d-block mb-2">Required Subjects:</strong>
        <p class="mb-0">${course.subjects || "Not specified"}</p>
      </div>
    </div>
  `;
}

// Course Search Implementation
const CourseSearch = {
  debounceTimeout: null,

  initialize() {
    const searchInput = document.getElementById("courseSearch");
    if (!searchInput) return;

    searchInput.value = AppState.modalState.courseSearchTerm;

    // Remove old event listener and add new one
    const newSearchInput = searchInput.cloneNode(true);
    searchInput.parentNode.replaceChild(newSearchInput, searchInput);

    newSearchInput.addEventListener("input", this.handleSearch.bind(this));

    // Initialize course count from the actual data
    this.initializeCourseCount();
  },

  initializeCourseCount() {
    const coursesList = document.getElementById("coursesList");
    if (coursesList) {
      const totalCourses =
        coursesList.querySelectorAll(".accordion-item").length;
      this.updateCourseCount(totalCourses);

      // Update the courses badge in the header
      const coursesCounter = document.querySelector(
        ".course-search-header .badge"
      );
      if (coursesCounter) {
        coursesCounter.textContent = `${totalCourses || 0} course${
          totalCourses !== 1 ? "s" : ""
        }`;
      }
    }
  },

  handleSearch(event) {
    clearTimeout(this.debounceTimeout);

    this.debounceTimeout = setTimeout(() => {
      const searchTerm = event.target.value.toLowerCase().trim();
      AppState.modalState.courseSearchTerm = searchTerm;
      this.filterCourses(searchTerm);
    }, 300);
  },

  filterCourses(searchTerm) {
    const coursesList = document.getElementById("coursesList");
    if (!coursesList) return;

    const items = coursesList.querySelectorAll(".accordion-item");
    let visibleCount = 0;

    items.forEach((item) => {
      const courseName = item
        .querySelector(".accordion-button")
        .textContent.toLowerCase();
      const isVisible = courseName.includes(searchTerm);

      this.toggleCourseVisibility(item, isVisible);
      if (isVisible) visibleCount++;
    });

    this.updateCourseCount(visibleCount);
    this.updateNoResultsMessage(visibleCount, searchTerm);
  },

  toggleCourseVisibility(item, isVisible) {
    if (isVisible) {
      item.style.display = "block";
      setTimeout(() => {
        item.style.opacity = "1";
        item.style.transform = "translateY(0)";
      }, 50);
    } else {
      item.style.opacity = "0";
      item.style.transform = "translateY(10px)";
      setTimeout(() => {
        item.style.display = "none";
      }, 300);
    }
  },

  updateCourseCount(visibleCount) {
    const countElement = document.getElementById("courseCount");
    if (countElement) {
      countElement.textContent = `${visibleCount || 0} course${
        visibleCount !== 1 ? "s" : ""
      }`;

      // Also update the courses badge in the header
      const coursesCounter = document.querySelector(
        ".course-search-header .badge"
      );
      if (coursesCounter) {
        coursesCounter.textContent = `${visibleCount || 0} course${
          visibleCount !== 1 ? "s" : ""
        }`;
      }
    }
  },

  updateNoResultsMessage(visibleCount, searchTerm) {
    const container = document.getElementById("coursesList");
    let message = document.getElementById("noCoursesFound");

    if (visibleCount === 0) {
      if (!message) {
        message = document.createElement("div");
        message.id = "noCoursesFound";
        message.className = "alert alert-info mt-3";
        message.innerHTML = `
                  <div class="d-flex align-items-center">
                      <i class="fas fa-info-circle me-3 fa-lg"></i>
                      <div>
                          <p class="mb-1"><strong>No matching courses found</strong></p>
                          <p class="mb-0 small">Try adjusting your search terms</p>
                      </div>
                  </div>
              `;
        container.appendChild(message);
      }
    } else if (message) {
      message.remove();
    }
  },
};

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

function showModalError(message) {
  const errorDiv = document.getElementById("modalErrorMessage");
  const loadingIndicator = document.getElementById("loadingIndicator");
  const institutionDetails = document.getElementById("institutionDetails");

  if (!errorDiv) return;

  loadingIndicator.style.display = "none";
  institutionDetails.style.display = "none";
  errorDiv.textContent = message;
  errorDiv.style.display = "block";
}

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

// Make AppState globally available
window.AppState = AppState;

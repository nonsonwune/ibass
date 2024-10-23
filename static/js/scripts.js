// static/js/scripts.js
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM fully loaded in scripts.js");
  initializeInstitutionModal();
  initializeVoting();
  initializeBookmarkButtons();
  if (window.isAuthenticated) {
    fetchUserVotes();
  }
});

function initializeInstitutionModal() {
  console.log("Initializing institution modal");

  const institutionModal = document.getElementById("institutionModal");
  if (!institutionModal) return;

  // Setup modal events
  institutionModal.addEventListener("show.bs.modal", function (event) {
    const button = event.relatedTarget;
    const uniId = button.getAttribute("data-uni-id");
    const selectedCourse = button.getAttribute("data-selected-course");
    resetModal();

    if (uniId) {
      fetchInstitutionDetails(uniId, selectedCourse);
    } else {
      showErrorMessage("Unable to retrieve institution details.");
    }
  });

  // Initialize course search when modal is shown
  institutionModal.addEventListener("shown.bs.modal", function () {
    setupCourseSearch();
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
      // Ensure selected_course is set in the data
      if (selectedCourse) {
        data.selected_course = selectedCourse;
      }
      populateModal(data);
    })
    .catch((error) => {
      console.error("Error fetching institution details:", error);
      showErrorMessage("Error loading institution details. Please try again.");
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

  // Hide/show appropriate elements
  elements.institutionDetails.style.display = "none";
  elements.modalErrorMessage.style.display = "none";
  elements.loadingIndicator.style.display = "block";

  // Clear content
  elements.institutionName.textContent = "";
  elements.institutionState.textContent = "";
  elements.institutionProgramType.textContent = "";
  elements.institutionWebsite.textContent = "";
  elements.institutionEstablished.textContent = "";
  elements.coursesList.innerHTML = "";
}
function setupCourseSearch() {
  const searchInput = document.getElementById("courseSearch");
  if (!searchInput) return;

  // Remove any existing event listeners
  searchInput.removeEventListener("input", handleCourseSearch);

  // Add new event listener
  searchInput.addEventListener("input", handleCourseSearch);

  // Clear search input
  searchInput.value = "";
}

function handleCourseSearch(event) {
  const searchTerm = event.target.value.toLowerCase();
  const accordionItems = document.querySelectorAll(
    "#coursesList .accordion-item"
  );

  accordionItems.forEach((item) => {
    const courseName = item
      .querySelector(".accordion-button")
      .textContent.toLowerCase();
    const isVisible = courseName.includes(searchTerm);

    // Handle visibility
    if (isVisible) {
      item.style.display = "block";
      // If it's a selected course, ensure it remains highlighted
      if (item.classList.contains("selected-course")) {
        item.classList.add("search-match");
      }
    } else {
      item.style.display = "none";
      item.classList.remove("search-match");
    }
  });

  // Update no results message
  const visibleItems = document.querySelectorAll(
    '#coursesList .accordion-item[style="display: block"]'
  );
  const noResultsMsg = document.getElementById("noCoursesFound");

  if (visibleItems.length === 0) {
    if (!noResultsMsg) {
      const message = document.createElement("div");
      message.id = "noCoursesFound";
      message.className = "alert alert-info mt-3";
      message.textContent = "No courses found matching your search.";
      document.getElementById("coursesList").appendChild(message);
    }
  } else if (noResultsMsg) {
    noResultsMsg.remove();
  }
}

function populateModal(uni) {
  console.log("Populating modal with data:", uni);

  const elements = {
    institutionName: document.getElementById("institutionName"),
    institutionState: document.getElementById("institutionState"),
    institutionProgramType: document.getElementById("institutionProgramType"),
    institutionWebsite: document.getElementById("institutionWebsite"),
    institutionEstablished: document.getElementById("institutionEstablished"),
    selectedCourseSection: document.getElementById("selectedCourseSection"),
    selectedCourseDetails: document.getElementById("selectedCourseDetails"),
    coursesList: document.getElementById("coursesList"),
  };

  // Populate basic institution information
  elements.institutionName.textContent = uni.university_name;
  elements.institutionState.textContent = uni.state;
  elements.institutionProgramType.textContent = uni.program_type;

  // Handle website
  if (uni.website) {
    elements.institutionWebsite.innerHTML = `<a href="${uni.website}" target="_blank" rel="noopener noreferrer">${uni.website}</a>`;
  } else {
    elements.institutionWebsite.textContent = "Not Available";
  }

  // Handle established date
  elements.institutionEstablished.textContent =
    uni.established || "Not Available";

  // Handle selected course if any
  if (uni.selected_course && uni.courses?.length > 0) {
    const selectedCourseData = uni.courses.find(
      (course) =>
        course.course_name.toLowerCase() === uni.selected_course.toLowerCase()
    );

    if (selectedCourseData) {
      elements.selectedCourseSection.style.display = "block";
      elements.selectedCourseDetails.innerHTML = `
        <h4 class="mb-3">${selectedCourseData.course_name}</h4>
        <div class="selected-course-requirements">
          <div class="mb-3">
            <h6 class="text-primary"><i class="fas fa-file-alt me-2"></i>UTME Requirements</h6>
            <p class="mb-0">${
              selectedCourseData.utme_requirements || "Not specified"
            }</p>
          </div>
          <div class="mb-3">
            <h6 class="text-primary"><i class="fas fa-door-open me-2"></i>Direct Entry Requirements</h6>
            <p class="mb-0">${
              selectedCourseData.direct_entry_requirements || "Not specified"
            }</p>
          </div>
          <div>
            <h6 class="text-primary"><i class="fas fa-books me-2"></i>Required Subjects</h6>
            <p class="mb-0">${
              selectedCourseData.subjects || "Not specified"
            }</p>
          </div>
        </div>
      `;
    } else {
      elements.selectedCourseSection.style.display = "none";
    }
  } else {
    elements.selectedCourseSection.style.display = "none";
  }

  // Populate courses list
  if (uni.courses && uni.courses.length > 0) {
    elements.coursesList.innerHTML = uni.courses
      .map((course, index) => {
        const isSelected =
          uni.selected_course &&
          course.course_name.toLowerCase() ===
            uni.selected_course.toLowerCase();

        return `
          <div class="accordion-item ${isSelected ? "selected-course" : ""}">
            <h2 class="accordion-header">
              <button class="accordion-button ${
                !isSelected ? "collapsed" : ""
              }" 
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
                ${createCourseHTML(course)}
              </div>
            </div>
          </div>
        `;
      })
      .join("");
  } else {
    elements.coursesList.innerHTML =
      '<p class="text-muted">No courses available for this institution.</p>';
  }

  // Show the institution details and hide loading
  document.getElementById("loadingIndicator").style.display = "none";
  document.getElementById("institutionDetails").style.display = "block";
}

function createCourseHTML(course) {
  return `
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
  `;
}

function createAccordionItem(course, index) {
  const collapseId = `collapseCourse${index}`;
  const headingId = `headingCourse${index}`;
  return `
          <div class="accordion-item">
            <h2 class="accordion-header" id="${headingId}">
              <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}" aria-expanded="false" aria-controls="${collapseId}">
                ${course.course_name}
              </button>
            </h2>
            <div id="${collapseId}" class="accordion-collapse collapse" aria-labelledby="${headingId}" data-bs-parent="#coursesAccordion">
              <div class="accordion-body">
                <p><strong>UTME Requirements:</strong> ${
                  course.utme_requirements || "N/A"
                }</p>
                <p><strong>Direct Entry Requirements:</strong> ${
                  course.direct_entry_requirements || "N/A"
                }</p>
                <p><strong>Subjects:</strong> ${course.subjects || "N/A"}</p>
              </div>
            </div>
          </div>
        `;
}

function showErrorMessage(message) {
  const errorDiv = document.getElementById("modalErrorMessage");
  if (errorDiv) {
    errorDiv.textContent = message;
    errorDiv.style.display = "block";
    document.getElementById("loadingIndicator").style.display = "none";
  } else {
    console.error("Error div not found:", message);
  }
}

function hideLoadingIndicator() {
  const loadingIndicator = document.getElementById("loadingIndicator");
  if (loadingIndicator) {
    loadingIndicator.style.display = "none";
  }
}

function initializeVoting() {
  const voteButtons = document.querySelectorAll(".vote-btn");
  voteButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const commentId = this.getAttribute("data-comment-id");
      const action = this.getAttribute("data-vote-type");
      vote(commentId, action, this);
    });
  });
}

function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute("content") : "";
}

function vote(commentId, action, buttonElement) {
  fetch(`/vote/${commentId}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": window.csrfToken,
      Accept: "application/json", // Ensure server returns JSON
    },
    credentials: "same-origin", // Include cookies in the request
  })
    .then((response) => {
      if (response.status === 401) {
        throw new Error("Please sign in to like or dislike comments.");
      }
      if (response.status === 403) {
        throw new Error("You do not have permission to perform this action.");
      }
      if (!response.ok) {
        throw new Error("An unexpected error occurred.");
      }
      return response.json();
    })
    .then((data) => {
      if (data.error) {
        alert(data.error);
      } else {
        // Validate response data
        if (
          typeof data.likes !== "number" ||
          typeof data.dislikes !== "number" ||
          typeof data.score !== "number" ||
          typeof data.user_votes !== "object"
        ) {
          throw new Error("Invalid data format received from server.");
        }
        updateVoteDisplay(commentId, data.likes, data.dislikes, data.score);
        applyUserVotes(data.user_votes);
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert(
        error.message ||
          "An error occurred while processing your vote. Please try again."
      );
    });
}

function updateVoteDisplay(commentId, likes, dislikes, score) {
  const commentElement = document
    .querySelector(`[data-comment-id="${commentId}"]`)
    .closest(".list-group-item");
  const likeButton = commentElement.querySelector(
    '.vote-btn[data-vote-type="like"]'
  );
  const dislikeButton = commentElement.querySelector(
    '.vote-btn[data-vote-type="dislike"]'
  );
  const scoreElement = commentElement.querySelector(".badge");

  if (likeButton)
    likeButton.innerHTML = `<i class="fas fa-thumbs-up"></i> Like (${likes})`;
  if (dislikeButton)
    dislikeButton.innerHTML = `<i class="fas fa-thumbs-down"></i> Dislike (${dislikes})`;
  if (scoreElement) scoreElement.textContent = `${score}`;
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
      if (response.redirected) {
        // Handle redirect (e.g., user is not authenticated)
        console.log("Redirected to login page.");
        return null;
      }

      if (!response.ok) {
        if (response.status === 401) {
          console.log("User not authenticated");
          return null;
        }
        throw new Error("Network response was not ok.");
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
    if (votes[commentId] === voteType) {
      button.classList.add("active");
    } else {
      button.classList.remove("active");
    }
  });
}
function initializeBookmarkButtons() {
  const bookmarkButtons = document.querySelectorAll(".bookmark-btn");
  console.log("Found bookmark buttons:", bookmarkButtons.length);

  bookmarkButtons.forEach((button) => {
    button.addEventListener("click", handleBookmarkClick);
  });
}

function handleBookmarkClick(event) {
  event.preventDefault();
  const button = this;
  const uniId = button.getAttribute("data-uni-id");
  const isBookmarked = button.classList.contains("btn-secondary");

  const url = isBookmarked ? `/remove_bookmark/${uniId}` : "/bookmark";
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
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        updateBookmarkButtonUI(button, !isBookmarked);
      } else {
        alert(data.message || "Bookmarking failed. Please try again.");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("An error occurred while bookmarking. Please try again.");
    });
}
function fetchUserBookmarks() {
  if (window.isAuthenticated) {
    fetch("/api/user_bookmarks", {
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": window.csrfToken,
        Accept: "application/json",
      },
    })
      .then((response) => response.json())
      .then((data) => {
        applyUserBookmarks(data);
      })
      .catch((error) => {
        console.error("Error fetching user bookmarks:", error);
      });
  }
}

function applyUserBookmarks(bookmarks) {
  document.querySelectorAll(".bookmark-btn").forEach((button) => {
    const uniId = button.getAttribute("data-uni-id");
    if (bookmarks.includes(parseInt(uniId))) {
      updateBookmarkButtonUI(button, true);
    } else {
      updateBookmarkButtonUI(button, false);
    }
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

document.addEventListener("DOMContentLoaded", function () {
  fetchUserBookmarks();
  // ... (other existing code)
});

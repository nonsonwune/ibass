// static/js/scripts.js

document.addEventListener("DOMContentLoaded", function () {
  initializeInstitutionModal();
  initializeVoting();
  fetchUserVotes();
});

function initializeInstitutionModal() {
  const institutionModal = document.getElementById("institutionModal");

  if (institutionModal) {
    institutionModal.addEventListener("show.bs.modal", function (event) {
      const button = event.relatedTarget;
      const uniId = button.getAttribute("data-uni-id");
      const selectedCourse = button.getAttribute("data-selected-course") || "";

      resetModal();

      if (uniId) {
        fetchInstitutionDetails(uniId, selectedCourse);
      } else {
        showErrorMessage("Unable to retrieve institution details.");
      }
    });
  }
}

function resetModal() {
  const elements = {
    institutionDetails: document.getElementById("institutionDetails"),
    modalErrorMessage: document.getElementById("modalErrorMessage"),
    loadingIndicator: document.getElementById("loadingIndicator"),
    institutionName: document.getElementById("institutionName"),
    institutionState: document.getElementById("institutionState"),
    institutionProgramType: document.getElementById("institutionProgramType"),
    searchCriteria: document.getElementById("searchCriteria"),
    selectedCourseContent: document.getElementById("selectedCourseContent"),
    institutionCoursesList: document.getElementById("institutionCoursesList"),
  };

  if (elements.institutionDetails)
    elements.institutionDetails.style.display = "none";
  if (elements.modalErrorMessage)
    elements.modalErrorMessage.style.display = "none";
  if (elements.loadingIndicator)
    elements.loadingIndicator.style.display = "block";

  if (elements.institutionName) elements.institutionName.textContent = "";
  if (elements.institutionState) elements.institutionState.textContent = "";
  if (elements.institutionProgramType)
    elements.institutionProgramType.textContent = "";
  if (elements.searchCriteria) elements.searchCriteria.textContent = "";
  if (elements.selectedCourseContent)
    elements.selectedCourseContent.innerHTML = "";
  if (elements.institutionCoursesList)
    elements.institutionCoursesList.innerHTML = "";
}

function fetchInstitutionDetails(uniId, selectedCourse) {
  console.log(
    `Fetching details for institution ID: ${uniId}, Selected Course: ${selectedCourse}`
  );
  fetch(
    `/api/institution/${uniId}?course=${encodeURIComponent(selectedCourse)}`
  )
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((uni) => {
      console.log("Received university data:", uni);
      populateModal(uni);
    })
    .catch((error) => {
      console.error("Error fetching institution details:", error);
      hideLoadingIndicator();
      showErrorMessage(
        `Error loading institution details. Please try again. Error: ${error.message}`
      );
    });
}

function populateModal(uni) {
  console.log("Populating modal with data:", uni);

  const elements = {
    institutionName: document.getElementById("institutionName"),
    institutionState: document.getElementById("institutionState"),
    institutionProgramType: document.getElementById("institutionProgramType"),
    searchCriteria: document.getElementById("searchCriteria"),
    selectedCourseDetails: document.getElementById("selectedCourseDetails"),
    selectedCourseContent: document.getElementById("selectedCourseContent"),
    institutionCoursesList: document.getElementById("institutionCoursesList"),
  };

  const missingElements = Object.entries(elements)
    .filter(([key, value]) => !value)
    .map(([key]) => key);

  if (missingElements.length > 0) {
    console.error("Missing elements:", missingElements);
    showErrorMessage("Required modal elements are missing.");
    return;
  }

  elements.institutionName.textContent = uni.university_name;
  elements.institutionState.textContent = uni.state;
  elements.institutionProgramType.textContent = uni.program_type;
  elements.searchCriteria.textContent =
    uni.search_type === "course"
      ? `Course: ${uni.selected_course}`
      : `Location: ${uni.state}`;

  // Populate selected course details
  if (uni.selected_course && uni.courses && uni.courses.length > 0) {
    const selectedCourseData = uni.courses.find(
      (course) =>
        course.course_name.toLowerCase() === uni.selected_course.toLowerCase()
    );
    if (selectedCourseData) {
      elements.selectedCourseContent.innerHTML =
        createCourseHTML(selectedCourseData);
      elements.selectedCourseDetails.style.display = "block";
    } else {
      elements.selectedCourseContent.innerHTML = `<p class="alert alert-warning">No details available for the selected course "${uni.selected_course}" in this institution.</p>`;
      elements.selectedCourseDetails.style.display = "block";
    }
  }

  // Populate all courses
  if (uni.courses && uni.courses.length > 0) {
    elements.institutionCoursesList.innerHTML = uni.courses
      .map((course, index) => createAccordionItem(course, index))
      .join("");
  } else {
    elements.institutionCoursesList.innerHTML =
      '<p class="alert alert-info">No courses available for this institution.</p>';
  }

  // Show the institution details and hide loading
  document.getElementById("loadingIndicator").style.display = "none";
  document.getElementById("institutionDetails").style.display = "block";
}

function createCourseHTML(course) {
  return `
          <div class="card mb-3">
            <div class="card-body">
              <h5 class="card-title">${course.course_name}</h5>
              <p><strong>UTME Requirements:</strong> ${
                course.utme_requirements || "N/A"
              }</p>
              <p><strong>Direct Entry Requirements:</strong> ${
                course.direct_entry_requirements || "N/A"
              }</p>
              <p><strong>Subjects:</strong> ${course.subjects || "N/A"}</p>
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
      "X-CSRFToken": getCsrfToken(),
      Accept: "application/json", // Added Accept header
    },
    credentials: "same-origin",
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
  if (scoreElement) scoreElement.textContent = `Score: ${score}`;
}

function fetchUserVotes() {
  fetch("/api/user_votes")
    .then((response) => {
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

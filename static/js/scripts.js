// static/js/scripts.js

document.addEventListener("DOMContentLoaded", function () {
  const institutionModal = document.getElementById("institutionModal");

  if (institutionModal) {
    institutionModal.addEventListener("show.bs.modal", function (event) {
      const button = event.relatedTarget;
      const uniId = button.getAttribute("data-uni-id");
      const selectedCourse = button.getAttribute("data-selected-course") || "";

      // Reset modal content
      resetModal();

      if (uniId) {
        fetchInstitutionDetails(uniId, selectedCourse);
      } else {
        showErrorMessage("Unable to retrieve institution details.");
      }
    });
  } else {
    console.error("Institution modal not found in the DOM");
  }

  /**
   * Resets the modal content to its initial state.
   */
  function resetModal() {
    // Hide content and show loading
    document.getElementById("institutionDetails").style.display = "none";
    document.getElementById("modalErrorMessage").style.display = "none";
    document.getElementById("loadingIndicator").style.display = "block";

    // Clear previous content
    document.getElementById("institutionName").textContent = "";
    document.getElementById("institutionState").textContent = "";
    document.getElementById("institutionProgramType").textContent = "";
    document.getElementById("searchCriteria").textContent = "";
    // Removed image references
    document.getElementById("selectedCourseContent").innerHTML = "";
    document.getElementById("institutionCoursesList").innerHTML = "";
  }

  /**
   * Fetches institution details from the API.
   * @param {number} uniId - The ID of the university.
   * @param {string} selectedCourse - The name of the selected course.
   */
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

  /**
   * Populates the modal with university and course data.
   * @param {object} uni - The university data received from the API.
   */
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
      uni.courses.forEach((course, index) => {
        const courseHTML = createAccordionItem(course, index);
        elements.institutionCoursesList.innerHTML += courseHTML;
      });
    } else {
      elements.institutionCoursesList.innerHTML =
        '<p class="alert alert-info">No courses available for this institution.</p>';
    }

    // Show the institution details and hide loading
    document.getElementById("loadingIndicator").style.display = "none";
    document.getElementById("institutionDetails").style.display = "block";
  }

  /**
   * Creates HTML for a course.
   * @param {object} course - The course data.
   * @returns {string} - HTML string representing the course.
   */
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

  /**
   * Creates HTML for an accordion item representing a course.
   * @param {object} course - The course data.
   * @param {number} index - The index of the course in the list.
   * @returns {string} - HTML string for the accordion item.
   */
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

  /**
   * Shows an error message within the modal.
   * @param {string} message - The error message to display.
   */
  function showErrorMessage(message) {
    const errorDiv = document.getElementById("modalErrorMessage");
    errorDiv.textContent = message;
    errorDiv.style.display = "block";
  }

  /**
   * Hides the loading indicator.
   */
  function hideLoadingIndicator() {
    const loadingIndicator = document.getElementById("loadingIndicator");
    if (loadingIndicator) {
      loadingIndicator.style.display = "none";
    }
  }
});

// app/static/js/institutionModal.js

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

// Expose functions globally
window.initializeInstitutionModal = initializeInstitutionModal;
window.handleModalShow = handleModalShow;
window.handleModalShown = handleModalShown;
window.handleModalHidden = handleModalHidden;
window.resetModal = resetModal;
window.fetchInstitutionDetails = fetchInstitutionDetails;
window.populateModal = populateModal;
window.createCourseHTML = createCourseHTML;
window.createCourseDetailsHTML = createCourseDetailsHTML;

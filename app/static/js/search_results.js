// app/static/js/search_results.js

document.addEventListener("DOMContentLoaded", function () {
  const loadingOverlay = document.getElementById("loadingOverlay");
  const filterForm = document.getElementById("filterForm");
  const searchForm = document.querySelector('form[action*="search_results"]');

  // Handle new search - clear filters
  if (searchForm) {
    searchForm.addEventListener("submit", function () {
      // Clear all saved filters when starting a new search
      localStorage.removeItem("filter_state");
      localStorage.removeItem("filter_type");
      localStorage.removeItem("filter_level");
    });
  }

  // Handle filter form submission
  if (filterForm) {
    filterForm.addEventListener("submit", function (e) {
      e.preventDefault();
      showLoadingOverlay(true);

      const formData = new FormData(this);
      const searchParams = new URLSearchParams(window.location.search);

      // Update search parameters
      ["state", "q"].forEach((key) => {
        if (formData.has(key)) {
          searchParams.set(key, formData.get(key));
        } else {
          searchParams.delete(key);
        }
      });

      // Handle multiple checkbox selections
      ["type", "level"].forEach((key) => {
        searchParams.delete(key);
        const values = formData.getAll(key);
        values.forEach((value) => {
          searchParams.append(key, value);
        });
      });

      // Navigate to filtered results
      window.location.href = `${
        window.location.pathname
      }?${searchParams.toString()}`;
    });
  }

  // Initialize tooltips
  initializeTooltips();

  // Restore filter state from URL parameters
  restoreFilterState();

  // Handle course modals
  initializeCourseModals();
});

// Show or hide loading overlay
function showLoadingOverlay(show) {
  const loadingOverlay = document.getElementById("loadingOverlay");
  if (loadingOverlay) {
    loadingOverlay.style.display = show ? "flex" : "none";
  }
}

// Restore filter state from URL parameters
function restoreFilterState() {
  const urlParams = new URLSearchParams(window.location.search);
  const filterForm = document.getElementById("filterForm");

  if (!filterForm) return;

  // Restore state filter
  const state = urlParams.get("state");
  if (state) {
    const stateSelect = filterForm.querySelector('select[name="state"]');
    if (stateSelect) {
      stateSelect.value = state;
    }
  }

  // Restore type checkboxes
  const types = urlParams.getAll("type");
  if (types.length > 0) {
    types.forEach((type) => {
      const typeCheckbox = filterForm.querySelector(
        `input[name="type"][value="${type}"]`
      );
      if (typeCheckbox) {
        typeCheckbox.checked = true;
      }
    });
  }

  // Restore level checkboxes
  const levels = urlParams.getAll("level");
  if (levels.length > 0) {
    levels.forEach((level) => {
      const levelCheckbox = filterForm.querySelector(
        `input[name="level"][value="${level}"]`
      );
      if (levelCheckbox) {
        levelCheckbox.checked = true;
      }
    });
  }
}

// Initialize tooltips
function initializeTooltips() {
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.forEach(function (tooltipTriggerEl) {
    new bootstrap.Tooltip(tooltipTriggerEl);
  });
}

// Initialize course modals
function initializeCourseModals() {
  const modals = document.querySelectorAll(".course-modal");
  modals.forEach((modal) => {
    modal.addEventListener("show.bs.modal", function () {
      const modalBody = this.querySelector(".modal-body");
      const courseId = this.getAttribute("data-course-id");

      // Add loading spinner
      modalBody.innerHTML = `
          <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading course details...</p>
          </div>`;

      // Fetch course details
      fetchCourseDetails(courseId, modalBody, this);
    });
  });
}

// Fetch course details from API
function fetchCourseDetails(courseId, modalBody, modalElement) {
  fetch(`/university/course/${courseId}`)
    .then((response) => response.json())
    .then((courseDetails) => {
      if (courseDetails.error) {
        modalBody.innerHTML = `
            <div class="alert alert-danger">
              <i class="fas fa-exclamation-circle me-2"></i>${courseDetails.error}
            </div>`;
        return;
      }

      let content = `
        <div class="course-requirements">
          <h6 class="mb-3">Entry Requirements</h6>
      `;

      // Add university name and requirements
      content += `
        <h6 class="mb-3">
          <i class="fas fa-university me-2 text-primary"></i>${
            courseDetails.university_name || "Unknown University"
          }
        </h6>
        <div class="mb-3">
          <strong>UTME Requirements:</strong>
          <p class="mb-2">${
            courseDetails.utme_requirements || "Not specified"
          }</p>
        </div>
        <div class="mb-3">
          <strong>Required Subjects:</strong>
          <p class="mb-2">${courseDetails.subjects || "Not specified"}</p>
        </div>
        <div>
          <strong>Direct Entry Requirements:</strong>
          <p class="mb-0">${
            courseDetails.direct_entry_requirements || "Not specified"
          }</p>
        </div>
      `;

      content += "</div>";
      modalBody.innerHTML = content;

      // Update "View Institution" button link
      const viewInstitutionBtn = modalElement.querySelector(
        ".view-institution-btn"
      );
      if (viewInstitutionBtn && courseDetails.university_id) {
        viewInstitutionBtn.href = `/university/institution/${courseDetails.university_id}`;
      }
    })
    .catch((error) => {
      console.error("Error fetching course details:", error);
      modalBody.innerHTML = `
          <div class="alert alert-danger">
            <i class="fas fa-exclamation-circle me-2"></i>Failed to load course details.
          </div>`;
    });
}

// Expose functions globally if needed
window.showLoadingOverlay = showLoadingOverlay;
window.initializeTooltips = initializeTooltips;
window.restoreFilterState = restoreFilterState;
window.initializeCourseModals = initializeCourseModals;

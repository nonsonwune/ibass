// app/static/js/recommend.js

document.addEventListener("DOMContentLoaded", function () {
  // Initialize application features
  initializeInstitutionModal();
  initializeModals();
  initializeFilterForm();
  initializePagination();
  
  // Use bookmark system from bookmarks.js
  if (window.initializeBookmarkSystem) {
    window.initializeBookmarkSystem();
    if (window.isAuthenticated && window.fetchUserBookmarks) {
      window.fetchUserBookmarks();
    }
  }
});

// Initialize Mobile Filters Modal
function initializeModals() {
  const filterToggleBtn = document.getElementById("filterToggleBtn");
  const mobileFiltersModal = document.getElementById("mobileFiltersModal");
  const mobileFilterModalBody = document.getElementById(
    "mobileFilterModalBody"
  );
  const filterForm = document.getElementById("filterForm");
  const mobileApplyFiltersBtn = document.getElementById(
    "mobileApplyFiltersBtn"
  );

  if (
    !filterToggleBtn ||
    !mobileFiltersModal ||
    !mobileFilterModalBody ||
    !filterForm ||
    !mobileApplyFiltersBtn
  ) {
    console.error("Filter modal elements not found.");
    return;
  }

  const modalInstance = new bootstrap.Modal(mobileFiltersModal, {
    backdrop: "static",
    keyboard: false,
  });

  filterToggleBtn.addEventListener("click", function () {
    // Clone the filter form and remove the submit button
    const clonedForm = filterForm.cloneNode(true);
    clonedForm.id = "mobileFilterForm";
    const submitBtn = clonedForm.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.remove();
    }

    // Append the cloned form to the modal body
    mobileFilterModalBody.innerHTML = "";
    mobileFilterModalBody.appendChild(clonedForm);

    // Show the modal
    modalInstance.show();
  });

  mobileApplyFiltersBtn.addEventListener("click", function () {
    const mobileForm = document.getElementById("mobileFilterForm");
    if (mobileForm) {
      // Transfer values from mobile form to main form
      const formData = new FormData(mobileForm);
      for (const [key, value] of formData.entries()) {
        const originalInput = filterForm.querySelector(`[name="${key}"]`);
        if (originalInput) {
          if (originalInput.type === "checkbox") {
            originalInput.checked = mobileForm.querySelector(
              `[name="${key}"]`
            ).checked;
          } else {
            originalInput.value = value;
          }
        }
      }

      // Hide modal and submit main form
      modalInstance.hide();
      filterForm.submit();
    }
  });
}

// Initialize Filter Form
function initializeFilterForm() {
  const filterForm = document.getElementById("filterForm");
  if (!filterForm) return;

  filterForm.addEventListener("submit", function (e) {
    e.preventDefault();
    showLoadingOverlay(true);
    this.submit();
  });
}

// Show or hide loading overlay
function showLoadingOverlay(show) {
  const loadingOverlay = document.getElementById("loadingOverlay");
  if (loadingOverlay) {
    loadingOverlay.style.display = show ? "flex" : "none";
  }
}

// Initialize Pagination
function initializePagination() {
  // No additional JavaScript needed for pagination if using standard links
}

// UI Utilities
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

// Export necessary functions
window.showToast = showToast;
window.showModalError = showModalError;
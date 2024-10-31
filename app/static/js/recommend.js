// app/static/js/recommend.js

document.addEventListener("DOMContentLoaded", function () {
  // Initialize application features
  initializeModals();
  initializeFilterForm();
  initializePagination();
  initializeInstitutionModal();
  initializeBookmarkSystem();

  if (window.isAuthenticated) {
    fetchUserBookmarks();
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

// Initialize Bookmark System
function initializeBookmarkSystem() {
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
  const isBookmarked = button.getAttribute("data-bookmarked") === "true";

  try {
    const url = isBookmarked
      ? `/api/remove_bookmark/${uniId}`
      : "/api/bookmark";
    const method = isBookmarked ? "DELETE" : "POST";
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
    button.setAttribute("data-bookmarked", "true");
    if (bookmarkText) bookmarkText.textContent = "Bookmarked";
    if (icon) {
      icon.classList.remove("fa-bookmark");
      icon.classList.add("fa-check");
    }
  } else {
    button.classList.remove("btn-secondary");
    button.classList.add("btn-outline-secondary");
    button.setAttribute("data-bookmarked", "false");
    if (bookmarkText) bookmarkText.textContent = "Bookmark";
    if (icon) {
      icon.classList.add("fa-bookmark");
      icon.classList.remove("fa-check");
    }
  }
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
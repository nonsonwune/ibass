// app/static/js/ui.js

function initializeTooltips() {
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.forEach(function (tooltipTriggerEl) {
    new bootstrap.Tooltip(tooltipTriggerEl);
  });
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

function showModalError(message) {
  const errorDiv = document.getElementById("modalErrorMessage");
  const loadingIndicator = document.getElementById("loadingIndicator");
  const institutionDetails = document.getElementById("institutionDetails");

  if (!errorDiv) return;

  if (loadingIndicator) loadingIndicator.style.display = "none";
  if (institutionDetails) institutionDetails.style.display = "none";
  errorDiv.textContent = message;
  errorDiv.style.display = "block";
}

// Expose functions globally
window.initializeTooltips = initializeTooltips;
window.showToast = showToast;
window.showModalError = showModalError;

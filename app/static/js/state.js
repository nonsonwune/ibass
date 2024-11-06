// app/static/js/state.js
const AppState = {
  modalState: {
    isLoading: false,
    currentInstitution: null,
    courseSearchTerm: "",
    selectedCourse: null,
  },

  pendingVotes: new Set(),

  setModalLoading(loading) {
    this.modalState.isLoading = Boolean(loading); // Ensure boolean
    this.updateModalUI();
  },

  updateModalUI() {
    const elements = {
      loadingIndicator: document.getElementById("loadingIndicator"),
      institutionDetails: document.getElementById("institutionDetails"),
      modalErrorMessage: document.getElementById("modalErrorMessage")
    };

    // Check all required elements exist
    if (!Object.values(elements).every(el => el)) {
      console.warn("Modal elements not found");
      return;
    }

    // Update UI based on state
    const { loadingIndicator, institutionDetails, modalErrorMessage } = elements;
    
    loadingIndicator.style.display = this.modalState.isLoading ? "block" : "none";
    institutionDetails.style.display = 
      (!this.modalState.isLoading && this.modalState.currentInstitution) ? "block" : "none";
    modalErrorMessage.style.display = "none"; // Reset error on state change
  },

  resetModalState() {
    this.modalState = {
      isLoading: false,
      currentInstitution: null,
      courseSearchTerm: "",
      selectedCourse: null,
    };
    this.updateModalUI();
    this.clearError(); // Clear any existing errors
  },

  setError(error) {
    const modalErrorMessage = document.getElementById("modalErrorMessage");
    if (modalErrorMessage) {
      modalErrorMessage.textContent = error ? String(error) : '';
      modalErrorMessage.style.display = error ? "block" : "none";
    }
  },

  clearError() {
    this.setError(null);
  },

  // Add validation helper
  isValidInstitutionData(data) {
    return data && typeof data === 'object' && 'id' in data;
  }
};

// Make AppState globally available
window.AppState = AppState;
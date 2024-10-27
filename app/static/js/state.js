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

// Make AppState globally available
window.AppState = AppState;

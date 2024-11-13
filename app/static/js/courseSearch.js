// app/static/js/courseSearch.js

const CourseSearch = {
  initialize() {
    this.searchInput = document.getElementById("courseSearch");
    this.coursesList = document.getElementById("coursesList");

    // Only initialize if both elements exist (for course-specific pages)
    if (this.searchInput && this.coursesList) {
      this.setupEventListeners();
    }
  },

  setupEventListeners() {
    let searchTimeout;

    this.searchInput.addEventListener("input", (e) => {
      clearTimeout(searchTimeout);
      const searchText = e.target.value.toLowerCase().trim();

      // Debounce search
      searchTimeout = setTimeout(() => {
        this.filterCourses(searchText);
      }, 300);
    });

    // Close expanded accordions when starting a new search
    this.searchInput.addEventListener("focus", () => {
      const expandedItems = this.coursesList.querySelectorAll(
        ".accordion-collapse.show"
      );
      expandedItems.forEach((item) => {
        const button =
          item.previousElementSibling.querySelector(".accordion-button");
        if (button) button.click();
      });
    });
  },

  filterCourses(searchText) {
    const courseItems = this.coursesList.querySelectorAll(".accordion-item");
    let visibleCount = 0;

    courseItems.forEach((item) => {
      const courseName = item
        .querySelector(".accordion-button")
        .textContent.toLowerCase();
      const isVisible = !searchText || courseName.includes(searchText);

      item.style.display = isVisible ? "" : "none";
      if (isVisible) visibleCount++;
    });

    // Update course count
    const courseCount = document.getElementById("courseCount");
    if (courseCount) {
      courseCount.textContent = `${visibleCount} course${
        visibleCount !== 1 ? "s" : ""
      }`;
    }

    // Show no results message if needed
    this.toggleNoResultsMessage(visibleCount === 0, searchText);
  },

  toggleNoResultsMessage(show, searchText) {
    let noResultsDiv = this.coursesList.querySelector(".no-results-message");

    if (show) {
      if (!noResultsDiv) {
        noResultsDiv = document.createElement("div");
        noResultsDiv.className =
          "no-results-message text-center py-4 text-muted";
        noResultsDiv.innerHTML = `
                    <i class="fas fa-search fa-2x mb-2"></i>
                    <p class="mb-0">No courses found matching "${searchText}"</p>
                `;
        this.coursesList.appendChild(noResultsDiv);
      }
    } else if (noResultsDiv) {
      noResultsDiv.remove();
    }
  },

  highlightMatch(text, searchText) {
    if (!searchText) return text;
    const regex = new RegExp(`(${searchText})`, "gi");
    return text.replace(regex, "<strong>$1</strong>");
  },
};

// Initialize when DOM is loaded - only if we're on a page that needs course search
document.addEventListener("DOMContentLoaded", () => {
  // Only initialize if we find the course search elements
  if (
    document.getElementById("courseSearch") &&
    document.getElementById("coursesList")
  ) {
    CourseSearch.initialize();
  }
});

// Export for use in other files
window.CourseSearch = CourseSearch;

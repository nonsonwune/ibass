// app/static/js/courseSearch.js

const CourseSearch = {
  debounceTimeout: null,

  initialize() {
    const searchInput = document.getElementById("courseSearch");
    if (!searchInput) return;

    searchInput.value = AppState.modalState.courseSearchTerm;

    // Remove old event listener and add new one
    const newSearchInput = searchInput.cloneNode(true);
    searchInput.parentNode.replaceChild(newSearchInput, searchInput);

    newSearchInput.addEventListener("input", this.handleSearch.bind(this));

    // Initialize course count from the actual data
    this.initializeCourseCount();
  },

  initializeCourseCount() {
    const coursesList = document.getElementById("coursesList");
    if (coursesList) {
      const totalCourses =
        coursesList.querySelectorAll(".accordion-item").length;
      this.updateCourseCount(totalCourses);

      // Update the courses badge in the header
      const coursesCounter = document.querySelector(
        ".course-search-header .badge"
      );
      if (coursesCounter) {
        coursesCounter.textContent = `${totalCourses || 0} course${
          totalCourses !== 1 ? "s" : ""
        }`;
      }
    }
  },

  handleSearch(event) {
    clearTimeout(this.debounceTimeout);

    this.debounceTimeout = setTimeout(() => {
      const searchTerm = event.target.value.toLowerCase().trim();
      AppState.modalState.courseSearchTerm = searchTerm;
      this.filterCourses(searchTerm);
    }, 300);
  },

  filterCourses(searchTerm) {
    const coursesList = document.getElementById("coursesList");
    if (!coursesList) return;

    const items = coursesList.querySelectorAll(".accordion-item");
    let visibleCount = 0;

    items.forEach((item) => {
      const courseName = item
        .querySelector(".accordion-button")
        .textContent.toLowerCase();
      const isVisible = courseName.includes(searchTerm);

      this.toggleCourseVisibility(item, isVisible);
      if (isVisible) visibleCount++;
    });

    this.updateCourseCount(visibleCount);
    this.updateNoResultsMessage(visibleCount, searchTerm);
  },

  toggleCourseVisibility(item, isVisible) {
    if (isVisible) {
      item.style.display = "block";
      setTimeout(() => {
        item.style.opacity = "1";
        item.style.transform = "translateY(0)";
      }, 50);
    } else {
      item.style.opacity = "0";
      item.style.transform = "translateY(10px)";
      setTimeout(() => {
        item.style.display = "none";
      }, 300);
    }
  },

  updateCourseCount(visibleCount) {
    const countElement = document.getElementById("courseCount");
    if (countElement) {
      countElement.textContent = `${visibleCount || 0} course${
        visibleCount !== 1 ? "s" : ""
      }`;

      // Also update the courses badge in the header
      const coursesCounter = document.querySelector(
        ".course-search-header .badge"
      );
      if (coursesCounter) {
        coursesCounter.textContent = `${visibleCount || 0} course${
          visibleCount !== 1 ? "s" : ""
        }`;
      }
    }
  },

  updateNoResultsMessage(visibleCount, searchTerm) {
    const container = document.getElementById("coursesList");
    let message = document.getElementById("noCoursesFound");

    if (visibleCount === 0) {
      if (!message) {
        message = document.createElement("div");
        message.id = "noCoursesFound";
        message.className = "alert alert-info mt-3";
        message.innerHTML = `
                    <div class="d-flex align-items-center">
                        <i class="fas fa-info-circle me-3 fa-lg"></i>
                        <div>
                            <p class="mb-1"><strong>No matching courses found</strong></p>
                            <p class="mb-0 small">Try adjusting your search terms</p>
                        </div>
                    </div>
                `;
        container.appendChild(message);
      }
    } else if (message) {
      message.remove();
    }
  },
};

// Expose CourseSearch globally
window.CourseSearch = CourseSearch;

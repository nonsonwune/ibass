// app/static/js/home.js

document.addEventListener("DOMContentLoaded", function () {
  // Constants and State Management
  const STATE = {
    selectedTypes: new Set(),
    currentCourses: [],
    isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream,
    prefersReducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)")
      .matches,
    isMobile: window.innerWidth <= 768,
    lastSearchQuery: "",
    selectedSuggestionIndex: -1,
  };

  // DOM Elements
  const DOM = {
    heroSection: document.getElementById("heroSection"),
    locationSelect: document.getElementById("location"),
    institutionTypesGrid: document.getElementById("institutionTypes"),
    nextStepBtn: document.getElementById("nextStep"),
    prevStepBtn: document.getElementById("prevStep"),
    findInstitutionBtn: document.getElementById("findInstitution"),
    courseSelect: document.getElementById("course"),
    courseSearch: document.getElementById("courseSearch"),
    loadingSpinner: document.getElementById("loadingSpinner"),
    step1: document.getElementById("step1"),
    step2: document.getElementById("step2"),
    courseSuggestions: document.getElementById("courseSuggestions"),
    scrollPrompt: document.querySelector(".scroll-prompt"),
    selectedTypesContainer: document.querySelector(".selected-types"),
  };

  // Ensure DOM elements exist
  if (!DOM.heroSection || !DOM.nextStepBtn || !DOM.locationSelect) {
    console.warn("Required DOM elements are missing. Exiting script.");
    return;
  }

  // Program Groups Configuration
  const PROGRAMME_GROUPS = {
    "ALL DEGREE AWARDING INSTITUTIONS": [
      "E-LEARNING UNIVERSITIES OF NIGERIA",
      "FEDERAL UNIVERSITIES",
      "FEDERAL UNIVERSITIES OF AGRICULTURE",
      "FEDERAL UNIVERSITIES OF HEALTH SCIENCES",
      "FEDERAL UNIVERSITIES OF TECHNOLOGY",
      "OPEN AND DISTANCE LEARNING PROGRAMMES",
      "OTHER DEGREE AWARDING INSTITUTIONS",
      "PRIVATE UNIVERSITIES",
      "SANDWICH PROGRAMMES",
      "STATE UNIVERSITIES",
      "STATE UNIVERSITIES OF AGRICULTURE",
      "STATE UNIVERSITIES OF MEDICAL SCIENCES",
      "STATE UNIVERSITIES OF TECHNOLOGY",
    ],
    "ALL NCE": [
      "FEDERAL COLLEGES OF EDUCATION",
      "STATE COLLEGES OF EDUCATION",
      "PRIVATE COLLEGES OF EDUCATION",
    ],
  };

  // Enhanced Utility Functions
  const UTILS = {
    debounce(func, wait) {
      if (window.debounce) {
        return window.debounce(func, wait);
      }
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    },

    showError(message, container) {
      const errorDiv = document.createElement("div");
      errorDiv.className = "alert alert-danger mt-3";
      errorDiv.role = "alert";
      errorDiv.textContent = message;
      container.insertAdjacentElement("beforebegin", errorDiv);
      setTimeout(() => errorDiv.remove(), 5000);
    },

    showLoading(show) {
      if (window.IconUtils) {
        IconUtils.setButtonLoading(DOM.findInstitutionBtn, show);
      }
      DOM.loadingSpinner.style.display = show ? "flex" : "none";
      requestAnimationFrame(() => {
        DOM.loadingSpinner.style.opacity = show ? "1" : "0";
        DOM.courseSelect.style.display = show ? "none" : "block";
        DOM.courseSearch.style.display = show ? "none" : "block";
        DOM.findInstitutionBtn.style.display = show ? "none" : "block";
      });
    },

    highlightMatch(text, query) {
      if (!query) return text;
      const cleanQuery = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const regex = new RegExp(`(${cleanQuery})`, "gi");
      return text.replace(regex, "<strong>$1</strong>");
    },

    createLoadingSpinner() {
      return `<div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
              </div>`;
    },
  };

  // Parallax Implementation
  const PARALLAX = {
    init() {
      if (STATE.isIOS || STATE.prefersReducedMotion) {
        DOM.heroSection.style.backgroundAttachment = "scroll";
        return;
      }

      window.addEventListener(
        "scroll",
        () => {
          const rect = DOM.heroSection.getBoundingClientRect();
          if (rect.bottom > 0 && rect.top < window.innerHeight) {
            requestAnimationFrame(this.updatePosition);
          }
        },
        { passive: true }
      );

      window
        .matchMedia("(prefers-reduced-motion: reduce)")
        .addEventListener("change", (e) => {
          STATE.prefersReducedMotion = e.matches;
          DOM.heroSection.style.backgroundAttachment = e.matches
            ? "scroll"
            : "fixed";
        });

      window.addEventListener(
        "resize",
        () => {
          STATE.isMobile = window.innerWidth <= 768;
          if (STATE.isMobile) {
            DOM.heroSection.style.backgroundAttachment = "scroll";
          } else if (!STATE.isIOS && !STATE.prefersReducedMotion) {
            DOM.heroSection.style.backgroundAttachment = "fixed";
          }
        },
        { passive: true }
      );
    },

    updatePosition() {
      if (STATE.isIOS || STATE.prefersReducedMotion) return;
      const scrolled = window.pageYOffset;
      const factor = STATE.isMobile ? 0.15 : 0.5;
      const yPos = -(scrolled * factor);
      DOM.heroSection.style.backgroundPositionY = `${yPos}px`;
    },
  };

  // Background Image Loading
  const preloadHeroImage = () => {
    const img = new Image();
    img.src = "/static/images/hero.png";
    img.onload = () => {
      DOM.heroSection.style.backgroundImage = `linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url('${img.src}')`;
      DOM.heroSection.classList.add("loaded");
    };
  };

  // Scroll prompt handler
  const handleScroll = () => {
    requestAnimationFrame(() => {
      DOM.scrollPrompt.style.opacity = window.pageYOffset > 100 ? "0" : "0.8";
    });
  };

  // Location Handler Implementation
  const LOCATION_HANDLER = {
    async loadLocations() {
      console.log("loadLocations called");
      try {
        const response = await fetch("/api/locations");
        if (!response.ok) throw new Error("Failed to load locations");
  
        const locations = await response.json();
        console.log("Locations fetched:", locations);
        this.populateLocations(locations);
      } catch (error) {
        console.error("Error loading locations:", error);
        UTILS.showError(
          "Failed to load locations. Please refresh the page.",
          DOM.locationSelect
        );
      }
    },

    populateLocations(locations) {
      DOM.locationSelect.innerHTML = '<option value="">Select a State</option>';

      locations.forEach((location) => {
        const option = document.createElement("option");
        option.value = location;
        option.textContent = location === "ALL" ? "ANY STATE" : location;
        DOM.locationSelect.appendChild(option);
      });
    },

    async handleLocationChange(selectedState) {
      // Reset state
      STATE.selectedTypes.clear();
      STATE.currentCourses = [];
      DOM.nextStepBtn.disabled = true;
      DOM.institutionTypesGrid.innerHTML = "";

      if (!selectedState) return;

      try {
        const url =
          selectedState === "ALL"
            ? "/api/programme_types"
            : `/api/programme_types?state=${encodeURIComponent(selectedState)}`;

        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to load programme types");

        const types = await response.json();
        INSTITUTION_HANDLER.createTypeCards(types);
        INSTITUTION_HANDLER.updateSelectedTypesDisplay();
      } catch (error) {
        console.error("Error loading programme types:", error);
        UTILS.showError(
          "Failed to load institution types. Please try again.",
          DOM.institutionTypesGrid
        );
      }
    },
  };

  // Institution Handler Implementation
  const INSTITUTION_HANDLER = {
    createTypeCards(types) {
      const sortedTypes = types
        .filter((type) => type !== "ALL_INSTITUTION_TYPES")
        .sort((a, b) => a.localeCompare(b));

      this.createSelectedTypesContainer();
      this.renderTypeCards(sortedTypes);
      this.addCardEventListeners();
    },

    createSelectedTypesContainer() {
      if (!DOM.selectedTypesContainer) {
        const container = document.createElement("div");
        container.className = "selected-types";
        container.setAttribute("aria-label", "Selected institution types");
        container.setAttribute("role", "region");
        container.setAttribute("aria-live", "polite");
        DOM.institutionTypesGrid.insertAdjacentElement(
          "beforebegin",
          container
        );
        DOM.selectedTypesContainer = container;
      }
      DOM.selectedTypesContainer.innerHTML = "";
    },

    renderTypeCards(types) {
      const getIcon = (type) => {
        if (window.IconUtils) {
          return IconUtils.getInstitutionIcon(type);
        }
        return this.getInstitutionIcon(type);
      };

      DOM.institutionTypesGrid.innerHTML = types
        .map(
          (type) => `
            <div 
                class="institution-card" 
                data-type="${type}"
                role="button"
                tabindex="0"
                aria-pressed="false"
                aria-label="${this.formatInstitutionType(type)}"
            >
                <i class="fas ${getIcon(
                  type
                )} mb-3 fa-2x" aria-hidden="true"></i>
                <h5 class="mb-2">${this.formatInstitutionType(type)}</h5>
                <p class="mb-0 small text-muted">Click to select</p>
            </div>
        `
        )
        .join("");
    },

    addCardEventListeners() {
      document.querySelectorAll(".institution-card").forEach((card) => {
        const handleSelection = () => {
          const type = card.dataset.type;
          if (STATE.selectedTypes.has(type)) {
            this.removeInstitutionType(type);
          } else {
            this.addInstitutionType(type);
          }
          DOM.nextStepBtn.disabled = STATE.selectedTypes.size === 0;
        };

        // Click handler
        card.addEventListener("click", handleSelection);

        // Keyboard handler
        card.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleSelection();
          }
        });
      });
    },

    addInstitutionType(type) {
      STATE.selectedTypes.add(type);
      const card = document.querySelector(
        `.institution-card[data-type="${type}"]`
      );
      if (card) {
        card.classList.add("selected");
        card.setAttribute("aria-pressed", "true");
      }
      this.addSelectedTypeBadge(type);
    },

    removeInstitutionType(type) {
      STATE.selectedTypes.delete(type);
      const card = document.querySelector(
        `.institution-card[data-type="${type}"]`
      );
      if (card) {
        card.classList.remove("selected");
        card.setAttribute("aria-pressed", "false");
      }
      this.removeSelectedTypeBadge(type);
    },

    updateSelectedTypesDisplay() {
      if (!DOM.selectedTypesContainer) return;
      DOM.selectedTypesContainer.innerHTML = "";
      Array.from(STATE.selectedTypes)
        .sort()
        .forEach((type) => this.addSelectedTypeBadge(type));
    },

    addSelectedTypeBadge(type) {
      if (!DOM.selectedTypesContainer) return;

      const badge = document.createElement("div");
      badge.className = "selected-type-badge";
      badge.dataset.type = type;
      badge.setAttribute("role", "status");
      badge.innerHTML = `
          ${this.formatInstitutionType(type)}
          <button 
              onclick="removeInstitutionType('${type}')"
              aria-label="Remove ${this.formatInstitutionType(type)}"
          >
              <i class="fas fa-times" aria-hidden="true"></i>
          </button>
      `;
      DOM.selectedTypesContainer.appendChild(badge);
    },

    removeSelectedTypeBadge(type) {
      const badge = document.querySelector(
        `.selected-type-badge[data-type="${type}"]`
      );
      if (badge) {
        badge.style.animation = "fadeOut 0.3s ease";
        setTimeout(() => badge.remove(), 300);
      }
    },

    formatInstitutionType(type) {
      return type
        .split(/[ _]/g)
        .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
        .join(" ");
    },

    getInstitutionIcon(type) {
      if (window.IconUtils) {
        return IconUtils.getInstitutionIcon(type);
      }

      const typeUpper = type.toUpperCase();
      if (typeUpper.includes("EDUCATION") && typeUpper.includes("TECHNICAL")) {
        return "fa-cog";
      }
      if (typeUpper.includes("POLYTECHNIC")) return "fa-industry";
      if (typeUpper.includes("UNIVERSITIES")) return "fa-university";
      if (typeUpper.includes("EDUCATION")) return "fa-chalkboard-teacher";
      if (typeUpper.includes("HEALTH") || typeUpper.includes("MEDICAL")) {
        return "fa-hospital";
      }
      if (typeUpper.includes("TECHNOLOGY")) return "fa-microchip";
      if (typeUpper.includes("AGRICULTURE")) return "fa-leaf";
      if (typeUpper.includes("DISTANCE") || typeUpper.includes("E-LEARNING")) {
        return "fa-laptop";
      }
      if (typeUpper.includes("COLLEGES")) return "fa-school";
      return "fa-graduation-cap";
    },
  };

  // Course Handler Implementation
  const COURSE_HANDLER = {
    async loadCourses(state, programTypes) {
      this.showLoading(true);

      try {
        const courses = await this.fetchCourses(state, programTypes);
        STATE.currentCourses = this.processCourses(courses);
        this.initializeSearchInterface();

        if (STATE.currentCourses.length === 0) {
          UTILS.showError(
            "No courses available for the selected location and institution types.",
            DOM.step2
          );
        }
      } catch (error) {
        console.error("Error loading courses:", error);
        UTILS.showError(`Failed to load courses: ${error.message}`, DOM.step2);
      } finally {
        this.showLoading(false);
      }
    },

    async fetchCourses(state, programTypes) {
      const programTypesString = Array.from(programTypes).join(",");
      const response = await fetch(
        `/api/courses?state=${encodeURIComponent(
          state
        )}&programme_type=${encodeURIComponent(programTypesString)}`
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.message || `HTTP error! status: ${response.status}`
        );
      }

      return response.json();
    },

    processCourses(courses) {
      if (!Array.isArray(courses)) {
        throw new Error("Invalid response format from server");
      }

      const coursesMap = new Map();

      courses.forEach((course) => {
        if (course.course_name === "ALL") return;

        const courseKey = course.course_name.toUpperCase();
        if (!coursesMap.has(courseKey)) {
          coursesMap.set(courseKey, {
            name: course.course_name,
            institutions: new Set([
              {
                name: course.university_name,
                state: course.state,
                type: course.program_type,
              },
            ]),
            details: {
              utme: course.utme_requirements,
              subjects: course.subjects,
              directEntry: course.direct_entry_requirements,
              abbreviation: course.abbrv,
            },
          });
        } else {
          coursesMap.get(courseKey).institutions.add({
            name: course.university_name,
            state: course.state,
            type: course.program_type,
          });
        }
      });

      return Array.from(coursesMap.values()).sort((a, b) =>
        a.name.localeCompare(b.name)
      );
    },

    initializeSearchInterface() {
      const searchInput = DOM.courseSearch;
      const suggestionsContainer = DOM.courseSuggestions;
      STATE.selectedSuggestionIndex = -1;

      this.showSearchInterface();
      this.attachSearchHandlers(searchInput, suggestionsContainer);
      this.attachKeyboardNavigation(searchInput, suggestionsContainer);
      this.attachClickHandlers(suggestionsContainer);
      this.resetSearchState();
    },

    showSearchInterface() {
      DOM.courseSearch.style.display = "block";
      DOM.courseSelect.style.display = "block";
      this.populateCourseSelect(STATE.currentCourses);
    },

    populateCourseSelect(courses) {
      DOM.courseSelect.innerHTML = `
      <option value="">Select a Course</option>
      <option value="ALL">ANY COURSE</option>
    `;

      courses.forEach((course) => {
        const option = document.createElement("option");
        option.value = course.name;
        option.dataset.institutions = JSON.stringify(
          Array.from(course.institutions)
        );
        option.textContent = `${course.name} (${course.institutions.size} ${
          course.institutions.size === 1 ? "institution" : "institutions"
        })`;
        DOM.courseSelect.appendChild(option);
      });
    },

    attachSearchHandlers(searchInput, suggestionsContainer) {
      const searchHandler = UTILS.debounce((event) => {
        const query = event.target.value.toLowerCase().trim();
        STATE.lastSearchQuery = query;

        if (!query) {
          suggestionsContainer.classList.remove("show");
          DOM.findInstitutionBtn.disabled = !DOM.courseSelect.value;
          this.populateCourseSelect(STATE.currentCourses);
          return;
        }

        const filteredCourses = STATE.currentCourses.filter((course) =>
          course.name.toLowerCase().includes(query)
        );

        this.showSuggestions(filteredCourses, query);
        this.populateCourseSelect(filteredCourses);
        STATE.selectedSuggestionIndex = -1;
      }, 300);

      searchInput.addEventListener("input", searchHandler);
    },

    attachKeyboardNavigation(searchInput, suggestionsContainer) {
      searchInput.addEventListener("keydown", (e) => {
        const suggestions = document.querySelectorAll(
          ".course-suggestion-item"
        );

        switch (e.key) {
          case "ArrowDown":
            e.preventDefault();
            STATE.selectedSuggestionIndex = Math.min(
              STATE.selectedSuggestionIndex + 1,
              suggestions.length - 1
            );
            this.updateSelection(suggestions, STATE.selectedSuggestionIndex);
            break;

          case "ArrowUp":
            e.preventDefault();
            STATE.selectedSuggestionIndex = Math.max(
              STATE.selectedSuggestionIndex - 1,
              -1
            );
            this.updateSelection(suggestions, STATE.selectedSuggestionIndex);
            break;

          case "Enter":
            e.preventDefault();
            if (
              STATE.selectedSuggestionIndex >= 0 &&
              suggestions[STATE.selectedSuggestionIndex]
            ) {
              this.selectSuggestion(suggestions[STATE.selectedSuggestionIndex]);
            }
            break;

          case "Escape":
            suggestionsContainer.classList.remove("show");
            STATE.selectedSuggestionIndex = -1;
            break;
        }
      });
    },

    attachClickHandlers(suggestionsContainer) {
      suggestionsContainer.addEventListener("click", (e) => {
        const suggestion = e.target.closest(".course-suggestion-item");
        if (suggestion) {
          this.selectSuggestion(suggestion);
        }
      });

      document.addEventListener("click", (e) => {
        if (
          !DOM.courseSearch.contains(e.target) &&
          !suggestionsContainer.contains(e.target)
        ) {
          suggestionsContainer.classList.remove("show");
        }
      });
    },

    showSuggestions(suggestions, query) {
      if (suggestions.length === 0) {
        DOM.courseSuggestions.classList.remove("show");
        return;
      }

      const html = suggestions
        .map(
          (course, index) => `
          <div 
              class="course-suggestion-item" 
              data-index="${index}" 
              data-value="${course.name}"
              data-institutions='${JSON.stringify(
                Array.from(course.institutions)
              )}'
              role="option"
              aria-selected="false"
          >
              <div class="course-name">
                  ${UTILS.highlightMatch(course.name, query)}
              </div>
              <div class="institution-count">
                  ${course.institutions.size} 
                  ${
                    course.institutions.size === 1
                      ? "institution"
                      : "institutions"
                  } available
              </div>
          </div>
        `
        )
        .join("");

      DOM.courseSuggestions.innerHTML = html;
      DOM.courseSuggestions.classList.add("show");
    },

    updateSelection(suggestions, selectedIndex) {
      suggestions.forEach((suggestion, index) => {
        suggestion.classList.toggle("active", index === selectedIndex);
        suggestion.setAttribute("aria-selected", index === selectedIndex);
        if (index === selectedIndex) {
          suggestion.scrollIntoView({ block: "nearest" });
        }
      });
    },

    selectSuggestion(suggestionElement) {
      const courseName = suggestionElement.dataset.value;
      const institutions = JSON.parse(suggestionElement.dataset.institutions);

      DOM.courseSearch.value = courseName;
      DOM.courseSuggestions.classList.remove("show");
      DOM.courseSelect.value = courseName;
      DOM.findInstitutionBtn.disabled = false;
    },

    showLoading(show) {
      UTILS.showLoading(show);
      if (!show) {
        DOM.findInstitutionBtn.disabled = true;
      }
    },

    resetSearchState() {
      DOM.courseSearch.value = "";
      DOM.findInstitutionBtn.disabled = true;
      STATE.lastSearchQuery = "";
      STATE.selectedSuggestionIndex = -1;
    },
  };

  // Navigation Handler Implementation
  const NAVIGATION_HANDLER = {
    initialize() {
      this.initializeStepNavigation();
      this.initializeButtonHandlers();
      this.initializeKeyboardNavigation();
    },

    initializeStepNavigation() {
      DOM.nextStepBtn.addEventListener("click", () => {
        if (DOM.locationSelect.value && STATE.selectedTypes.size > 0) {
          this.moveToStep2();
        }
      });

      DOM.prevStepBtn.addEventListener("click", () => {
        this.moveToStep1();
      });
    },

    initializeButtonHandlers() {
      DOM.findInstitutionBtn.addEventListener("click", () => {
        this.handleFindInstitution();
      });

      DOM.courseSelect.addEventListener("change", (e) => {
        const selectedOption = e.target.options[e.target.selectedIndex];
        if (selectedOption.value) {
          DOM.courseSearch.value =
            selectedOption.value === "ALL" ? "" : selectedOption.value;
          DOM.findInstitutionBtn.disabled = false;
        } else {
          DOM.courseSearch.value = "";
          DOM.findInstitutionBtn.disabled = true;
        }
        DOM.courseSuggestions.classList.remove("show");
      });
    },

    initializeKeyboardNavigation() {
      document.addEventListener("keydown", (e) => {
        if (DOM.step2.classList.contains("active")) {
          if (e.key === "Escape") {
            this.moveToStep1();
          } else if (e.key === "Enter" && !DOM.findInstitutionBtn.disabled) {
            this.handleFindInstitution();
          }
        }
      });
    },

    moveToStep2() {
      const wizardContainer = document.getElementById("wizard-container");
      wizardContainer.scrollIntoView({
        behavior: STATE.prefersReducedMotion ? "auto" : "smooth",
        block: "start",
      });

      setTimeout(
        () => {
          DOM.step1.classList.remove("active");
          DOM.step1.setAttribute("aria-hidden", "true");
          DOM.step2.classList.add("active");
          DOM.step2.setAttribute("aria-hidden", "false");

          COURSE_HANDLER.loadCourses(
            DOM.locationSelect.value,
            STATE.selectedTypes
          );
        },
        STATE.prefersReducedMotion ? 0 : 500
      );
    },

    moveToStep1() {
      DOM.step2.classList.remove("active");
      DOM.step2.setAttribute("aria-hidden", "true");
      DOM.step1.classList.add("active");
      DOM.step1.setAttribute("aria-hidden", "false");
    },

    handleFindInstitution() {
      const selectedOption =
        DOM.courseSelect.options[DOM.courseSelect.selectedIndex];
      const selectedLocation = DOM.locationSelect.value;
      const selectedCourse = selectedOption.value;

      const params = new URLSearchParams({
        location: selectedLocation === "ALL" ? "" : selectedLocation,
        programme_type: Array.from(STATE.selectedTypes).join(","),
        course: selectedCourse === "ALL" ? "" : selectedCourse,
        institutions: selectedOption.dataset.institutions || "",
      });

      window.location.href = `/recommend?${params}`;
    },
  };

  // Accessibility Handler Implementation
  const ACCESSIBILITY_HANDLER = {
    initialize() {
      this.setupLiveRegion();
      this.setupKeyboardNavigation();
      this.setupFocusManagement();
      this.setupReducedMotionHandling();
    },

    setupLiveRegion() {
      const liveRegion = document.createElement("div");
      liveRegion.setAttribute("aria-live", "polite");
      liveRegion.setAttribute("aria-atomic", "true");
      liveRegion.className = "visually-hidden";
      document.body.appendChild(liveRegion);
    },

    setupKeyboardNavigation() {
      DOM.institutionTypesGrid.addEventListener("keydown", (e) => {
        if (e.target.classList.contains("institution-card")) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            e.target.click();
          }
        }
      });

      [DOM.locationSelect, DOM.courseSelect].forEach((select) => {
        select.addEventListener("keydown", (e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            select.click();
          }
        });
      });
    },

    setupFocusManagement() {
      [DOM.step1, DOM.step2].forEach((step) => {
        this.trapFocus(step);
      });

      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.attributeName === "class") {
            const element = mutation.target;
            if (element.classList.contains("active")) {
              const firstFocusable = element.querySelector(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
              );
              if (firstFocusable) {
                firstFocusable.focus();
              }
            }
          }
        });
      });

      [DOM.step1, DOM.step2].forEach((step) => {
        observer.observe(step, { attributes: true });
      });
    },

    setupReducedMotionHandling() {
      const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
      const handleReducedMotionChange = (e) => {
        STATE.prefersReducedMotion = e.matches;
        document.documentElement.style.scrollBehavior = e.matches
          ? "auto"
          : "smooth";
      };

      mediaQuery.addEventListener("change", handleReducedMotionChange);
      handleReducedMotionChange(mediaQuery);
    },

    trapFocus(element) {
      const focusableElements = element.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstFocusable = focusableElements[0];
      const lastFocusable = focusableElements[focusableElements.length - 1];

      element.addEventListener("keydown", (e) => {
        if (e.key === "Tab") {
          if (e.shiftKey && document.activeElement === firstFocusable) {
            e.preventDefault();
            lastFocusable.focus();
          } else if (!e.shiftKey && document.activeElement === lastFocusable) {
            e.preventDefault();
            firstFocusable.focus();
          }
        }
      });
    },
  };

  // Global remove institution type function
  window.removeInstitutionType = function (type) {
    INSTITUTION_HANDLER.removeInstitutionType(type);
    DOM.nextStepBtn.disabled = STATE.selectedTypes.size === 0;
  };

  // Initialize Application
  const initializeApp = () => {
    // Initialize core features
    PARALLAX.init();
    preloadHeroImage();

    // Set up scroll event listener
    window.addEventListener("scroll", handleScroll, { passive: true });

    // Load initial data
    LOCATION_HANDLER.loadLocations();

    // Set up location change handler
    DOM.locationSelect.addEventListener("change", (e) =>
      LOCATION_HANDLER.handleLocationChange(e.target.value)
    );

    // Initialize navigation
    NAVIGATION_HANDLER.initialize();

    // Initialize accessibility features
    ACCESSIBILITY_HANDLER.initialize();

    // Set up error handling for uncaught promises
    window.addEventListener("unhandledrejection", (event) => {
      console.error("Unhandled promise rejection:", event.reason);
      UTILS.showError(
        "An unexpected error occurred. Please try again or refresh the page.",
        document.querySelector(".wizard-step.active") || document.body
      );
    });

    // Handle browser back/forward buttons
    window.addEventListener("popstate", () => {
      if (DOM.step2.classList.contains("active")) {
        NAVIGATION_HANDLER.moveToStep1();
      }
    });

    // Handle window resize events
    let resizeTimeout;
    window.addEventListener(
      "resize",
      () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
          STATE.isMobile = window.innerWidth <= 768;
          if (DOM.courseSuggestions.classList.contains("show")) {
            const suggestionItems = document.querySelectorAll(
              ".course-suggestion-item"
            );
            if (
              suggestionItems.length > 0 &&
              STATE.selectedSuggestionIndex >= 0
            ) {
              suggestionItems[STATE.selectedSuggestionIndex].scrollIntoView({
                block: "nearest",
              });
            }
          }
        }, 250);
      },
      { passive: true }
    );

    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== "undefined" && bootstrap.Tooltip) {
      const tooltipTriggerList = document.querySelectorAll(
        '[data-bs-toggle="tooltip"]'
      );
      [...tooltipTriggerList].map(
        (tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl)
      );
    }
  };

  // Start the application
  initializeApp();
});

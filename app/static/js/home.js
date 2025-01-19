// Define DOM elements first
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
    featuredSection: document.getElementById("featuredSection"),
    featuredGrid: document.getElementById("featuredInstitutions"),
    featuredPagination: document.getElementById("featuredPagination"),
    featuredPrev: document.getElementById("prevFeatured"),
    featuredNext: document.getElementById("nextFeatured"),
    loadingPlaceholder: document.getElementById("loadingPlaceholder")
};

// Define state management
const STATE = {
    selectedTypes: new Set(),
    currentCourses: [],
    lastSearchQuery: "",
    selectedSuggestionIndex: -1
};

// Define UTILS object
const UTILS = {
    showError(message, container) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-3';
        errorDiv.role = 'alert';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-circle me-2"></i>
            ${message}
        `;
        container.insertAdjacentElement('beforebegin', errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    },

    showLoading(show, element) {
        if (show) {
            element.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
        }
    }
};

// Then define your handlers
const LOCATION_HANDLER = {
    async loadLocations() {
        console.log("loadLocations called");
        try {
            const response = await fetch("/api/locations");
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("Raw response data:", data);
            
            if (Array.isArray(data)) {
                this.populateLocations(data);
            } else {
                throw new Error('Invalid locations data format');
            }
        } catch (error) {
            console.error("Error loading locations:", error);
            UTILS.showError(
                "Failed to load locations. Please refresh the page.",
                DOM.locationSelect
            );
        }
    },

    populateLocations(locations) {
        console.log("populateLocations called with:", locations);
        DOM.locationSelect.innerHTML = '<option value="">Select a State</option>';

        locations.forEach((location) => {
            const option = document.createElement("option");
            option.value = location;
            option.textContent = location === "ALL" ? "ANY STATE" : location;
            DOM.locationSelect.appendChild(option);
        });
    }
};

const INSTITUTION_HANDLER = {
    async handleLocationChange(selectedState) {
        if (!selectedState) return;

        try {
            const response = await fetch(
                selectedState === "ALL" 
                    ? '/api/programme-types'
                    : `/api/programme-types/${encodeURIComponent(selectedState)}`
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log("Creating type cards for:", data.data);
            this.createTypeCards(data.data);
        } catch (error) {
            console.error("Error loading programme types:", error);
            UTILS.showError(
                "Failed to load institution types. Please try again.",
                DOM.institutionTypesGrid
            );
        }
    },

    createTypeCards(types) {
        const container = DOM.institutionTypesGrid;
        container.innerHTML = '';

        types.forEach(type => {
            const card = document.createElement('div');
            card.className = 'institution-card';
            card.setAttribute('data-type', type.name);
            card.setAttribute('role', 'button');
            card.setAttribute('tabindex', '0');
            card.setAttribute('aria-pressed', 'false');

            const icon = this.getInstitutionIcon(type.category);
            const badgeColor = this.getInstitutionTypeBadgeColor(type.institution_type);

            card.innerHTML = `
                <i class="fas ${icon} mb-3 fa-2x" aria-hidden="true"></i>
                <h5 class="mb-2">${this.formatInstitutionType(type.name)}</h5>
                <span class="badge bg-${badgeColor}">${type.institution_type || 'OTHER'}</span>
                <p class="mb-0 small text-muted">Click to select</p>
            `;

            card.addEventListener('click', () => this.toggleTypeSelection(card));
            container.appendChild(card);
        });
    },

    toggleTypeSelection(card) {
        const type = card.getAttribute('data-type');
        if (STATE.selectedTypes.has(type)) {
            this.removeType(type);
        } else {
            this.addType(type);
        }
        this.updateSelectedTypesDisplay();
    },

    addType(type) {
        STATE.selectedTypes.add(type);
        const card = document.querySelector(`.institution-card[data-type="${type}"]`);
        if (card) {
            card.classList.add('selected');
            card.setAttribute('aria-pressed', 'true');
        }
    },

    removeType(type) {
        STATE.selectedTypes.delete(type);
        const card = document.querySelector(`.institution-card[data-type="${type}"]`);
        if (card) {
            card.classList.remove('selected');
            card.setAttribute('aria-pressed', 'false');
        }
    },

    updateSelectedTypesDisplay() {
        if (!DOM.selectedTypesContainer) return;
        DOM.selectedTypesContainer.innerHTML = '';
        STATE.selectedTypes.forEach(type => {
            const badge = document.createElement('div');
            badge.className = 'selected-type-badge';
            badge.innerHTML = `
                ${this.formatInstitutionType(type)}
                <button onclick="INSTITUTION_HANDLER.removeType('${type}')" aria-label="Remove ${type}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            DOM.selectedTypesContainer.appendChild(badge);
        });
        DOM.nextStepBtn.disabled = STATE.selectedTypes.size === 0;
    },

    formatInstitutionType(type) {
        return type.split(/[ _]/)
            .map(word => word.charAt(0) + word.slice(1).toLowerCase())
            .join(' ');
    },

    getInstitutionIcon(category) {
        const categoryMap = {
            'UNIVERSITY': 'fa-university',
            'POLYTECHNIC': 'fa-industry',
            'COLLEGE': 'fa-school',
            'SCHOOL': 'fa-graduation-cap',
            'OTHER': 'fa-building'
        };
        return categoryMap[category?.toUpperCase()] || categoryMap['OTHER'];
    },

    getInstitutionTypeBadgeColor(type) {
        const colorMap = {
            'FEDERAL': 'primary',
            'STATE': 'success',
            'PRIVATE': 'info',
            'OTHER': 'secondary'
        };
        return colorMap[type?.toUpperCase()] || colorMap['OTHER'];
    }
};

const COURSE_HANDLER = {
    async loadCourses(selectedLocation, selectedTypes) {
        try {
            console.log("Loading courses for location:", selectedLocation, "types:", selectedTypes);
            
            // Show loading spinner
            if (DOM.loadingSpinner) {
                DOM.loadingSpinner.style.display = "flex";
            }
            
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            const response = await fetch('/api/courses', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({
                    state: selectedLocation,
                    programme_type: selectedTypes.join(','),
                    load_all: true
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log("Courses loaded:", data);

            STATE.currentCourses = data.courses;
            this.populateCourseSelect(data.courses);
            this.setupCourseSearch();

        } catch (error) {
            console.error("Error loading courses:", error);
            UTILS.showError(
                `Failed to load courses: ${error.message}`,
                DOM.step2
            );
        } finally {
            // Hide loading spinner regardless of success or failure
            if (DOM.loadingSpinner) {
                DOM.loadingSpinner.style.display = "none";
            }
        }
    },

    populateCourseSelect(courses) {
        console.log("Populating course select with", courses.length, "courses");
        DOM.courseSelect.innerHTML = `
            <option value="">Select a Course</option>
            <option value="ALL">ANY COURSE</option>
        `;

        courses.forEach(course => {
            const option = document.createElement('option');
            option.value = course.course_name;
            option.textContent = `${course.course_name} (${course.institution_count} institutions)`;
            DOM.courseSelect.appendChild(option);
        });

        DOM.findInstitutionBtn.disabled = true;
        DOM.courseSelect.addEventListener('change', (e) => {
            DOM.findInstitutionBtn.disabled = !e.target.value;
            if (e.target.value) {
                DOM.courseSearch.value = e.target.value === 'ALL' ? '' : e.target.value;
            }
        });
    },

    setupFindInstitutionButton() {
        DOM.findInstitutionBtn.addEventListener('click', () => {
            const selectedLocation = DOM.locationSelect.value;
            const selectedTypes = Array.from(STATE.selectedTypes);
            const selectedCourse = DOM.courseSelect.value;

            const params = new URLSearchParams({
                location: selectedLocation === 'ALL' ? '' : selectedLocation,
                programme_type: selectedTypes.join(','),
                course: selectedCourse === 'ALL' ? '' : selectedCourse
            });

            window.location.href = `/recommend?${params.toString()}`;
        });
    },

    setupCourseSearch() {
        if (!DOM.courseSearch || !DOM.courseSuggestions) return;

        let searchTimeout;
        DOM.courseSearch.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const searchText = e.target.value.toLowerCase().trim();
            
            // Clear suggestions if search is empty
            if (!searchText) {
                DOM.courseSuggestions.classList.remove('show');
                return;
            }

            // Debounce search
            searchTimeout = setTimeout(() => {
                const filteredCourses = STATE.currentCourses.filter(course => 
                    course.course_name.toLowerCase().includes(searchText)
                );
                this.showCourseSuggestions(filteredCourses, searchText);
            }, 300);
        });

        // Close suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!DOM.courseSearch.contains(e.target) && !DOM.courseSuggestions.contains(e.target)) {
                DOM.courseSuggestions.classList.remove('show');
            }
        });
    },

    showCourseSuggestions(courses, searchText) {
        if (courses.length === 0) {
            DOM.courseSuggestions.classList.remove('show');
            return;
        }

        const html = courses.slice(0, 10).map(course => `
            <div class="course-suggestion-item" data-value="${course.course_name}">
                <div class="course-name">
                    ${this.highlightMatch(course.course_name, searchText)}
                </div>
                <div class="institution-count">
                    ${course.institution_count} institution${course.institution_count !== 1 ? 's' : ''} available
                </div>
            </div>
        `).join('');

        DOM.courseSuggestions.innerHTML = html;
        DOM.courseSuggestions.classList.add('show');

        // Add click handlers for suggestions
        DOM.courseSuggestions.querySelectorAll('.course-suggestion-item').forEach(item => {
            item.addEventListener('click', () => {
                const courseName = item.dataset.value;
                DOM.courseSearch.value = courseName;
                DOM.courseSelect.value = courseName;
                DOM.courseSuggestions.classList.remove('show');
                DOM.findInstitutionBtn.disabled = false;
            });
        });
    },

    highlightMatch(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<strong>$1</strong>');
    }
};

const NAVIGATION_HANDLER = {
    moveToStep2() {
        if (DOM.locationSelect.value && STATE.selectedTypes.size > 0) {
            console.log("Moving to step 2");
            const wizardContainer = document.getElementById("wizard-container");
            wizardContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });

            setTimeout(() => {
                DOM.step1.classList.remove("active");
                DOM.step1.setAttribute("aria-hidden", "true");
                DOM.step2.classList.add("active");
                DOM.step2.setAttribute("aria-hidden", "false");

                // Load courses for selected location and types
                COURSE_HANDLER.loadCourses(
                    DOM.locationSelect.value,
                    Array.from(STATE.selectedTypes)
                );
            }, 500);
        }
    },

    moveToStep1() {
        console.log("Moving back to step 1");
        DOM.step2.classList.remove("active");
        DOM.step2.setAttribute("aria-hidden", "true");
        DOM.step1.classList.add("active");
        DOM.step1.setAttribute("aria-hidden", "false");
    }
};

const FEATURED_HANDLER = {
    currentPage: 0,
    itemsPerPage: 3,
    institutions: [],

    async loadFeaturedInstitutions() {
        try {
            if (DOM.loadingPlaceholder) {
                DOM.loadingPlaceholder.style.display = 'block';
            }
            if (DOM.featuredGrid) {
                DOM.featuredGrid.style.display = 'none';
            }

            const response = await fetch("/api/featured-institutions");
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            console.log("Featured institutions data:", data);

            if (data.status === 'success' && Array.isArray(data.institutions)) {
                this.institutions = data.institutions;
            } else {
                throw new Error('Invalid data format from API');
            }
            
            if (DOM.loadingPlaceholder) {
                DOM.loadingPlaceholder.style.display = 'none';
            }
            if (DOM.featuredGrid) {
                DOM.featuredGrid.style.display = 'grid';
            }

            this.renderInstitutions();
            this.setupPagination();
            this.initializeObserver();
        } catch (error) {
            console.error("Error loading featured institutions:", error);
            if (DOM.loadingPlaceholder) {
                DOM.loadingPlaceholder.style.display = 'none';
            }
            if (DOM.featuredGrid) {
                UTILS.showError(
                    "Failed to load featured institutions. Please refresh the page.",
                    DOM.featuredGrid
                );
            }
        }
    },

    renderInstitutions() {
        if (!DOM.featuredGrid || !Array.isArray(this.institutions)) return;

        const start = this.currentPage * this.itemsPerPage;
        const end = start + this.itemsPerPage;
        const pageInstitutions = this.institutions.slice(start, end);

        DOM.featuredGrid.innerHTML = pageInstitutions.map(institution => `
            <div class="institution-card" data-aos="fade-up">
                <div class="institution-header">
                    <div class="institution-icon">
                        <i class="fas fa-university"></i>
                    </div>
                    <h3 class="h5 mb-2">${institution.name}</h3>
                    <div class="section-badge">
                        <span class="badge bg-primary">${institution.type}</span>
                    </div>
                </div>
                <div class="institution-body">
                    <div class="institution-stat">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${institution.state}</span>
                    </div>
                    <div class="institution-stat">
                        <i class="fas fa-book"></i>
                        <span>${institution.courses_count} Courses</span>
                    </div>
                    <a href="/institution/${institution.id}" class="btn btn-primary mt-3 w-100">
                        View Details
                    </a>
                </div>
            </div>
        `).join('');

        // Trigger AOS animations
        if (window.AOS) {
            window.AOS.refresh();
        }
    },

    setupPagination() {
        if (!DOM.featuredPagination) return;

        const totalPages = Math.ceil(this.institutions.length / this.itemsPerPage);
        DOM.featuredPagination.innerHTML = Array.from({ length: totalPages }, (_, i) => `
            <div class="pagination-dot ${i === this.currentPage ? 'active' : ''}" 
                 data-page="${i}" 
                 role="button" 
                 tabindex="0"
                 aria-label="Page ${i + 1}">
            </div>
        `).join('');

        DOM.featuredPagination.addEventListener('click', (e) => {
            const dot = e.target.closest('.pagination-dot');
            if (dot) {
                this.currentPage = parseInt(dot.dataset.page);
                this.updateUI();
            }
        });

        // Update navigation buttons state
        if (DOM.featuredPrev) {
            DOM.featuredPrev.disabled = this.currentPage === 0;
        }
        if (DOM.featuredNext) {
            DOM.featuredNext.disabled = this.currentPage === totalPages - 1;
        }
    },

    updateUI() {
        this.renderInstitutions();
        this.setupPagination();
    },

    initializeObserver() {
        if (!DOM.featuredSection || !window.IntersectionObserver) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    DOM.featuredGrid.classList.add('loaded');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        observer.observe(DOM.featuredSection);
    },

    setupEventListeners() {
        if (DOM.featuredPrev) {
            DOM.featuredPrev.addEventListener('click', () => {
                if (this.currentPage > 0) {
                    this.currentPage--;
                    this.updateUI();
                }
            });
        }

        if (DOM.featuredNext) {
            DOM.featuredNext.addEventListener('click', () => {
                const totalPages = Math.ceil(this.institutions.length / this.itemsPerPage);
                if (this.currentPage < totalPages - 1) {
                    this.currentPage++;
                    this.updateUI();
                }
            });
        }
    }
};

// Finally, add the event listener
document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM Content Loaded");
    
    // Verify DOM elements
    console.log("Location Select Element:", DOM.locationSelect);
    
    // Initialize handlers
    if (LOCATION_HANDLER && typeof LOCATION_HANDLER.loadLocations === 'function') {
        console.log("Calling loadLocations");
        LOCATION_HANDLER.loadLocations();
    } else {
        console.error("LOCATION_HANDLER not properly initialized");
    }

    // Add change event listener for location select
    DOM.locationSelect.addEventListener('change', async function(event) {
        console.log("Location changed to:", event.target.value);
        await INSTITUTION_HANDLER.handleLocationChange(event.target.value);
    });

    // Add navigation button handlers
    DOM.nextStepBtn.addEventListener("click", () => {
        console.log("Next step button clicked");
        NAVIGATION_HANDLER.moveToStep2();
    });

    DOM.prevStepBtn.addEventListener("click", () => {
        console.log("Previous step button clicked");
        NAVIGATION_HANDLER.moveToStep1();
    });

    // Initialize find institution button
    if (DOM.findInstitutionBtn) {
        COURSE_HANDLER.setupFindInstitutionButton();
    }

    // Initialize featured institutions
    FEATURED_HANDLER.loadFeaturedInstitutions();
    FEATURED_HANDLER.setupEventListeners();
});

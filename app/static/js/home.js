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
    step3: document.getElementById("step3"),
    courseSuggestions: document.getElementById("courseSuggestions"),
    scrollPrompt: document.querySelector(".scroll-prompt"),
    selectedTypesContainer: document.querySelector(".selected-types"),
    featuredSection: document.getElementById("featuredSection"),
    featuredGrid: document.getElementById("featuredInstitutions"),
    featuredPagination: document.getElementById("featuredPagination"),
    featuredPrev: document.getElementById("prevFeatured"),
    featuredNext: document.getElementById("nextFeatured"),
    loadingPlaceholder: document.getElementById("loadingPlaceholder"),
    prevStepFromType: document.getElementById("prevStepFromType")
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

// Define Error Handling Utilities
const ErrorHandler = {
    showError(message, container = null) {
        console.error(message);
        const errorEl = document.createElement('div');
        errorEl.className = 'alert alert-danger';
        errorEl.innerHTML = `
            <i class="fas fa-exclamation-circle me-2"></i>
            ${message}
        `;
        
        if (container) {
            container.innerHTML = '';
            container.appendChild(errorEl);
        } else {
            document.body.appendChild(errorEl);
            setTimeout(() => errorEl.remove(), 5000);
        }
    },
    
    async wrapAsync(fn, errorMessage) {
        try {
            return await fn();
        } catch (error) {
            console.error(error);
            this.showError(errorMessage);
            throw error;
        }
    }
};

// Define Component Initialization
const ComponentManager = {
    components: new Set(),
    
    register(id, initFn) {
        this.components.add({ id, initFn });
    },
    
    async initializeAll() {
        for (const component of this.components) {
            try {
                await component.initFn();
            } catch (error) {
                ErrorHandler.showError(`Failed to initialize ${component.id}`);
            }
        }
    }
};

// Define LOCATION_HANDLER with proper binding
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
                // Use arrow function to maintain this context
                await this.populateLocations(data);
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

    populateLocations: function(locations) {
        console.log("populateLocations called with:", locations);
        if (!DOM.locationSelect) {
            console.error("Location select element not found");
            return;
        }
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
            
            // Automatically move to step 2 after loading institution types
            NAVIGATION_HANDLER.moveToStep2();
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
    updateStepIndicators(currentStep) {
        const steps = document.querySelectorAll('.step-indicators .step');
        steps.forEach((step, index) => {
            if (index < currentStep) {
                step.classList.add('completed');
                step.classList.remove('active');
            } else if (index === currentStep) {
                step.classList.add('active');
                step.classList.remove('completed');
            } else {
                step.classList.remove('active', 'completed');
            }
        });
    },

    moveToStep2() {
        if (DOM.locationSelect.value) {
            console.log("Moving to step 2");
            const wizardContainer = document.getElementById("wizard-container");
            wizardContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });

            // First, blur any focused element in step 1
            if (document.activeElement && DOM.step1.contains(document.activeElement)) {
                document.activeElement.blur();
            }

            setTimeout(() => {
                // Remove inert from step 2 before making it active
                DOM.step2.removeAttribute('inert');
                DOM.step2.classList.add("active");
                
                // Focus the first interactive element in step 2
                const firstInteractive = DOM.step2.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
                if (firstInteractive) {
                    firstInteractive.focus();
                }

                // Now safe to make step 1 inert
                DOM.step1.classList.remove("active");
                DOM.step1.setAttribute('inert', '');
                
                this.updateStepIndicators(1);
            }, 500);
        }
    },

    moveToStep3() {
        if (STATE.selectedTypes.size > 0) {
            console.log("Moving to step 3");
            const wizardContainer = document.getElementById("wizard-container");
            wizardContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });

            // First, blur any focused element in step 2
            if (document.activeElement && DOM.step2.contains(document.activeElement)) {
                document.activeElement.blur();
            }

            setTimeout(() => {
                // Remove inert from step 3 before making it active
                DOM.step3.removeAttribute('inert');
                DOM.step3.classList.add("active");
                
                // Focus the course search input in step 3
                if (DOM.courseSearch) {
                    DOM.courseSearch.focus();
                }

                // Now safe to make step 2 inert
                DOM.step2.classList.remove("active");
                DOM.step2.setAttribute('inert', '');
                
                this.updateStepIndicators(2);

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
        
        // First, blur any focused element in step 2
        if (document.activeElement && DOM.step2.contains(document.activeElement)) {
            document.activeElement.blur();
        }

        // Remove inert from step 1 before making it active
        DOM.step1.removeAttribute('inert');
        DOM.step1.classList.add("active");
        
        // Focus the location select
        if (DOM.locationSelect) {
            DOM.locationSelect.focus();
        }

        // Now safe to make step 2 inert
        DOM.step2.classList.remove("active");
        DOM.step2.setAttribute('inert', '');
        
        this.updateStepIndicators(0);
    },

    moveBackFromStep3() {
        console.log("Moving back to step 2");
        
        // First, blur any focused element in step 3
        if (document.activeElement && DOM.step3.contains(document.activeElement)) {
            document.activeElement.blur();
        }

        // Remove inert from step 2 before making it active
        DOM.step2.removeAttribute('inert');
        DOM.step2.classList.add("active");
        
        // Focus the first selected institution type card or the grid
        const firstSelected = DOM.institutionTypesGrid.querySelector('.institution-card.selected') || DOM.institutionTypesGrid;
        if (firstSelected) {
            firstSelected.focus();
        }

        // Now safe to make step 3 inert
        DOM.step3.classList.remove("active");
        DOM.step3.setAttribute('inert', '');
        
        this.updateStepIndicators(1);
    }
};

// Remove duplicate DOMContentLoaded listener and consolidate initialization
document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM Content Loaded");
    
    // Register components with proper binding
    ComponentManager.register('locations', () => LOCATION_HANDLER.loadLocations());
    ComponentManager.register('featured', () => {
        if (typeof FEATURED_HANDLER === 'undefined') {
            console.error('FEATURED_HANDLER not loaded. Ensure featured.js is included before home.js');
            return;
        }
        return FEATURED_HANDLER.loadFeaturedInstitutions();
    });
    
    // Initialize all components
    ComponentManager.initializeAll();
    
    // Add event listeners
    if (DOM.locationSelect) {
        DOM.locationSelect.addEventListener('change', async (event) => {
            console.log("Location changed to:", event.target.value);
            await INSTITUTION_HANDLER.handleLocationChange(event.target.value);
        });
    }

    if (DOM.nextStepBtn) {
        DOM.nextStepBtn.addEventListener("click", () => {
            console.log("Next step button clicked");
            if (DOM.step1.classList.contains("active")) {
                NAVIGATION_HANDLER.moveToStep2();
            } else if (DOM.step2.classList.contains("active")) {
                NAVIGATION_HANDLER.moveToStep3();
            }
        });
    }

    // Add event listener for the new back button in step 2
    if (DOM.prevStepFromType) {
        DOM.prevStepFromType.addEventListener("click", () => {
            console.log("Back to location selection clicked");
            NAVIGATION_HANDLER.moveToStep1();
            // Clear selected institution types when going back
            STATE.selectedTypes.clear();
            INSTITUTION_HANDLER.updateSelectedTypesDisplay();
        });
    }

    if (DOM.prevStepBtn) {
        DOM.prevStepBtn.addEventListener("click", () => {
            console.log("Previous step button clicked");
            if (DOM.step2.classList.contains("active")) {
                NAVIGATION_HANDLER.moveToStep1();
            } else if (DOM.step3.classList.contains("active")) {
                NAVIGATION_HANDLER.moveBackFromStep3();
            }
        });
    }

    if (DOM.findInstitutionBtn) {
        COURSE_HANDLER.setupFindInstitutionButton();
    }

    // Setup featured institutions event listeners
    if (typeof FEATURED_HANDLER !== 'undefined' && FEATURED_HANDLER.setupEventListeners) {
        FEATURED_HANDLER.setupEventListeners();
    }
});

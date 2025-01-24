// Featured institutions functionality
function initFeaturedInstitutions() {
    const container = document.getElementById('featuredInstitutions');
    const loadingPlaceholder = document.getElementById('loadingPlaceholder');

    function createInstitutionCard(institution) {
        return `
            <div class="institution-card" data-aos="fade-up">
                <div class="institution-header">
                    <div class="institution-icon">
                        <i class="fas fa-university"></i>
                    </div>
                    <h3 class="institution-name">${institution.name}</h3>
                </div>
                <div class="institution-details">
                    <div class="institution-stat">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${institution.state}</span>
                    </div>
                    <div class="institution-stat">
                        <i class="fas fa-graduation-cap"></i>
                        <span>${institution.type}</span>
                    </div>
                    <div class="institution-stat">
                        <i class="fas fa-book"></i>
                        <span>${institution.courses_count} Courses</span>
                    </div>
                </div>
                <a href="/institution/${institution.id}" 
                   class="btn btn-primary mt-4 w-100">
                    View Details <i class="fas fa-arrow-right ms-2"></i>
                </a>
            </div>
        `;
    }

    // Fetch and render featured institutions
    fetch('/api/featured-institutions')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                loadingPlaceholder.style.display = 'none';
                const institutionsHtml = data.institutions
                    .map(createInstitutionCard)
                    .join('');
                container.innerHTML = institutionsHtml;
                // Reinitialize AOS for new elements
                AOS.refresh();
            } else {
                throw new Error(data.message);
            }
        })
        .catch(error => {
            loadingPlaceholder.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    Failed to load featured institutions. Please try again later.
                </div>
            `;
            console.error('Error:', error);
        });
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', initFeaturedInstitutions);

// Loading State Management
const LoadingManager = {
    show(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        container.innerHTML = `
            <div class="loading-state text-center py-4">
                <div class="spinner-grow text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted mb-0">Loading institutions...</p>
            </div>
        `;
    },
    
    hide(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.querySelector('.loading-state')?.remove();
    }
};

// Featured institutions handler
const FEATURED_HANDLER = {
    currentPage: 0,
    itemsPerPage: 3,
    institutions: [],

    createInstitutionCard(institution) {
        return `
            <div class="institution-card" data-aos="fade-up">
                <div class="institution-header">
                    <div class="institution-icon">
                        <i class="fas fa-university"></i>
                    </div>
                    <h3 class="institution-name">${institution.name}</h3>
                </div>
                <div class="institution-details">
                    <div class="institution-stat">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${institution.state}</span>
                    </div>
                    <div class="institution-stat">
                        <i class="fas fa-graduation-cap"></i>
                        <span>${institution.type}</span>
                    </div>
                    <div class="institution-stat">
                        <i class="fas fa-book"></i>
                        <span>${institution.courses_count} Courses</span>
                    </div>
                </div>
                <a href="/institution/${institution.id}" 
                   class="btn btn-primary mt-4 w-100">
                    View Details <i class="fas fa-arrow-right ms-2"></i>
                </a>
            </div>
        `;
    },

    async loadFeaturedInstitutions() {
        const containerId = 'featuredInstitutions';
        try {
            LoadingManager.show(containerId);
            
            const response = await fetch('/api/featured-institutions');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            console.log("Featured institutions data:", data);
            
            if (data.status === 'success' && Array.isArray(data.institutions)) {
                this.institutions = data.institutions;
                this.renderInstitutions();
                this.setupPagination();
                this.initializeObserver();
            } else {
                throw new Error('Invalid data format from API');
            }
        } catch (error) {
            console.error("Error loading featured institutions:", error);
            ErrorHandler.showError('Failed to load featured institutions', 
                document.getElementById(containerId));
        } finally {
            LoadingManager.hide(containerId);
        }
    },

    renderInstitutions() {
        const container = document.getElementById('featuredInstitutions');
        if (!container) return;

        const start = this.currentPage * this.itemsPerPage;
        const end = start + this.itemsPerPage;
        const pageInstitutions = this.institutions.slice(start, end);

        container.innerHTML = pageInstitutions
            .map(inst => this.createInstitutionCard(inst))
            .join('');

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

// Remove duplicate initialization
// The initialization is now handled in home.js

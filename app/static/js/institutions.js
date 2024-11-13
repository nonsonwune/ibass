document.addEventListener('DOMContentLoaded', function() {
    const filterForm = document.getElementById('institutionFilterForm');
    const filterToggleBtn = document.getElementById('filterToggleBtn');
    const filterModal = document.getElementById('filterModal');
    const mobileFilterContainer = document.getElementById('mobileFilterContainer');
    const institutionsGrid = document.getElementById('institutionsGrid');
    const searchInput = document.getElementById('institutionSearch');
    
    // Debounce function to limit how often the search is performed
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Add these variables at the top
    let searchTimeout;
    let currentSearchRequest;
    let isSearching = false;

    // Add this function to combine search and filter parameters
    function getCombinedParams() {
        const searchTerm = searchInput.value.toLowerCase();
        const formData = new FormData(filterForm);
        const params = new URLSearchParams();

        // Add search term if exists
        if (searchTerm) {
            params.set('search', searchTerm);
        }

        // Add filter parameters
        for (let [key, value] of formData.entries()) {
            if (value) {
                params.append(key, value);
            }
        }

        return params;
    }

    // Function to perform the search
    async function performSearch() {
        const loadingIndicator = document.querySelector('.search-loading');
        
        try {
            if (currentSearchRequest) {
                currentSearchRequest.abort();
            }

            loadingIndicator?.classList.add('active');
            isSearching = true;

            const params = getCombinedParams();
            params.set('page', '1'); // Reset to first page when searching

            const controller = new AbortController();
            currentSearchRequest = controller;

            const response = await fetch(`/api/search_institutions?${params.toString()}`, {
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();

            if (data.status === 'success') {
                // Update URL without reloading
                const newUrl = `${window.location.pathname}?${params.toString()}`;
                window.history.pushState({ path: newUrl }, '', newUrl);

                updateInstitutionsGrid(data.institutions);
                updateResultsCount(data.count);
                
                if (data.pagination) {
                    updatePagination(data.pagination);
                }
            } else {
                throw new Error(data.message);
            }

        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Search error:', error);
            showErrorMessage();
        } finally {
            loadingIndicator?.classList.remove('active');
            isSearching = false;
            currentSearchRequest = null;
        }
    }

    // Function to update the grid with new results
    function updateInstitutionsGrid(institutions) {
        institutionsGrid.innerHTML = '';
        
        if (institutions.length === 0) {
            const noResultsMsg = document.createElement('div');
            noResultsMsg.className = 'text-center py-5';
            noResultsMsg.innerHTML = `
                <i class="fas fa-search fa-3x text-muted mb-3"></i>
                <h4 class="mb-3">No Institutions Found</h4>
                <p class="text-muted">No institutions match your search criteria.</p>
            `;
            institutionsGrid.appendChild(noResultsMsg);
            return;
        }

        institutions.forEach(inst => {
            const card = document.createElement('div');
            card.className = 'col-md-6 col-lg-4';
            card.innerHTML = `
                <div class="card h-100 institution-card">
                    <div class="card-body">
                        <h5 class="card-title">${inst.name}</h5>
                        <div class="institution-details">
                            <p class="location">
                                <i class="fas fa-map-marker-alt me-2"></i>
                                ${inst.state}
                            </p>
                            <p class="type">
                                <i class="fas fa-building me-2"></i>
                                ${inst.type}
                            </p>
                        </div>
                        <div class="institution-stats">
                            <span class="badge bg-light text-dark">
                                <i class="fas fa-graduation-cap me-1"></i>
                                ${inst.courses_count} Courses
                            </span>
                        </div>
                        <a href="/institution/${inst.id}" 
                           class="btn btn-primary w-100 mt-3">
                            View Details
                        </a>
                    </div>
                </div>
            `;
            institutionsGrid.appendChild(card);
        });
    }

    // Add keyboard shortcut handler
    function handleSearchKeyboard(event) {
        if (event.key === 'Escape') {
            clearSearch();
        } else if (event.key === '/' && document.activeElement !== searchInput) {
            event.preventDefault();
            searchInput.focus();
        }
    }

    // Update the clearSearch function
    function clearSearch() {
        if (searchInput) {
            searchInput.value = '';
            // Immediately trigger the search when cleared
            performSearch();
            searchInput.focus();
        }
    }

    // Update the event listeners for the search input
    if (searchInput) {
        // Handle both input and clearing
        searchInput.addEventListener('input', debounce(function(e) {
            // This will handle both typing and clearing via backspace/delete
            performSearch();
        }, 300));
        
        // Handle clearing via the clear button or Escape key
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                clearSearch();
            }
        });

        // Handle clearing via the clear button
        document.querySelector('.clear-search')?.addEventListener('click', clearSearch);
    }

    // Existing filter form handling
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        performSearch();
    });

    // Handle mobile filter toggle
    filterToggleBtn.addEventListener('click', function() {
        const filterFormClone = filterForm.cloneNode(true);
        mobileFilterContainer.innerHTML = '';
        mobileFilterContainer.appendChild(filterFormClone);
        
        const modal = new bootstrap.Modal(filterModal);
        modal.show();
    });

    // Apply filters function
    function applyFilters() {
        const formData = new FormData(filterForm);
        const params = new URLSearchParams();

        for (let [key, value] of formData.entries()) {
            if (value) {
                params.append(key, value);
            }
        }

        // Add page parameter if exists
        const currentPage = new URLSearchParams(window.location.search).get('page');
        if (currentPage) {
            params.set('page', currentPage);
        }

        // Update URL and reload
        window.location.href = `${window.location.pathname}?${params.toString()}`;
    }

    // Restore filter state from URL
    function restoreFilterState() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // Restore filters
        urlParams.forEach((value, key) => {
            const element = filterForm.querySelector(`[name="${key}"]`);
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = true;
                } else {
                    element.value = value;
                }
            }
        });
    }

    // Initialize
    restoreFilterState();

    // Helper function to update results count
    function updateResultsCount(count) {
        const resultsCount = document.querySelector('.results-count');
        if (resultsCount) {
            resultsCount.textContent = count;
        }
    }

    // Helper function to show error message
    function showErrorMessage() {
        const noResultsMsg = document.getElementById('noResultsMessage') || 
                            document.createElement('div');
        noResultsMsg.id = 'noResultsMessage';
        noResultsMsg.className = 'text-center py-5';
        noResultsMsg.innerHTML = `
            <i class="fas fa-exclamation-circle fa-3x text-danger mb-3"></i>
            <h4 class="mb-3">Error</h4>
            <p class="text-muted">An error occurred while searching. Please try again.</p>
        `;
        
        if (!document.getElementById('noResultsMessage')) {
            institutionsGrid.appendChild(noResultsMsg);
        }
    }

    // Add function to update pagination
    function updatePagination(paginationData) {
        const paginationContainer = document.querySelector('nav[aria-label="Page navigation"]');
        if (paginationContainer && paginationData) {
            // Update pagination UI based on the new data
            // This will depend on your pagination structure
            // You might want to create a separate function for this
        }
    }

    // Update the initialization to restore search state
    function restoreSearchState() {
        const urlParams = new URLSearchParams(window.location.search);
        const searchTerm = urlParams.get('search');
        if (searchInput && searchTerm) {
            searchInput.value = searchTerm;
        }
    }

    // Call this in your initialization
    restoreSearchState();

    // Add change event listeners to filter inputs
    document.querySelectorAll('.filter-checkbox, .filter-select').forEach(input => {
        input.addEventListener('change', debounce(() => {
            performSearch();
        }, 300));
    });

    // Update the mobile filter handling
    function initializeMobileFilters() {
        const filterToggleBtn = document.getElementById("filterToggleBtn");
        const mobileFiltersModal = document.getElementById("mobileFiltersModal");
        const mobileFilterModalBody = document.getElementById("mobileFilterModalBody");
        const filterForm = document.getElementById("institutionFilterForm");
        const mobileApplyFiltersBtn = document.getElementById("mobileApplyFiltersBtn");

        if (!filterToggleBtn || !mobileFiltersModal || !mobileFilterModalBody || !filterForm || !mobileApplyFiltersBtn) {
            console.error("Filter modal elements not found.");
            return;
        }

        const modalInstance = new bootstrap.Modal(mobileFiltersModal, {
            backdrop: "static",
            keyboard: false,
        });

        filterToggleBtn.addEventListener("click", function() {
            // Clone the filter form and prepare it for the modal
            const clonedForm = filterForm.cloneNode(true);
            clonedForm.id = "mobileFilterForm";
            
            // Remove the original submit button
            const submitBtn = clonedForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.remove();
            }

            // Clear the modal body and append the cloned form
            mobileFilterModalBody.innerHTML = "";
            mobileFilterModalBody.appendChild(clonedForm);

            // Show the modal
            modalInstance.show();
        });

        mobileApplyFiltersBtn.addEventListener("click", function() {
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

                // Hide modal and perform search
                modalInstance.hide();
                performSearch();
            }
        });
    }

    // Initialize mobile filters
    initializeMobileFilters();
}); 
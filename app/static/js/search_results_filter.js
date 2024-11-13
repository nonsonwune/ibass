document.addEventListener('DOMContentLoaded', function() {
    // Get references to elements
    const filterToggleBtn = document.getElementById('filterToggleBtn');
    const mobileFiltersModal = document.getElementById('mobileFiltersModal');
    const filterForm = document.getElementById('filterForm');
    const mobileFilterModalBody = document.getElementById('mobileFilterModalBody');
    const mobileApplyFiltersBtn = document.getElementById('mobileApplyFiltersBtn');

    // Check if all elements exist before adding event listeners
    if (!filterToggleBtn || !mobileFiltersModal || !filterForm || !mobileFilterModalBody || !mobileApplyFiltersBtn) {
        console.error('One or more required elements not found');
        return;
    }

    // When filter button is clicked, show modal
    filterToggleBtn.addEventListener('click', function() {
        try {
            // Clone the filter form into the modal
            const filterFormClone = filterForm.cloneNode(true);
            
            // Ensure the hidden query input is preserved
            const originalQueryInput = filterForm.querySelector('input[name="q"]');
            const clonedQueryInput = filterFormClone.querySelector('input[name="q"]');
            
            if (originalQueryInput && clonedQueryInput) {
                clonedQueryInput.value = originalQueryInput.value;
            }

            // Clear previous content and append the clone
            mobileFilterModalBody.innerHTML = '';
            mobileFilterModalBody.appendChild(filterFormClone);

            // Show the modal
            const modal = new bootstrap.Modal(mobileFiltersModal);
            modal.show();
        } catch (error) {
            console.error('Error showing filter modal:', error);
        }
    });

    // When apply button is clicked
    mobileApplyFiltersBtn.addEventListener('click', function() {
        try {
            // Get the form from modal
            const modalForm = mobileFilterModalBody.querySelector('form');
            if (modalForm) {
                // Get the search query from the original form
                const originalQuery = filterForm.querySelector('input[name="q"]')?.value;
                
                // Ensure the query is set in the modal form
                const modalQueryInput = modalForm.querySelector('input[name="q"]');
                if (modalQueryInput && originalQuery) {
                    modalQueryInput.value = originalQuery;
                }

                // Create FormData from the modal form
                const formData = new FormData(modalForm);
                
                // Build URL parameters
                const params = new URLSearchParams();
                formData.forEach((value, key) => {
                    if (value) {
                        params.append(key, value);
                    }
                });

                // Redirect to the search results page with the filters
                window.location.href = `${window.location.pathname}?${params.toString()}`;
            } else {
                console.error('Form not found in modal');
            }
        } catch (error) {
            console.error('Error applying filters:', error);
        }
    });

    // Function to restore filter state from URL
    function restoreFilterState() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // Restore state filter
        const stateSelect = filterForm.querySelector('select[name="state"]');
        const state = urlParams.get('state');
        if (stateSelect && state) {
            stateSelect.value = state;
        }

        // Restore type filters
        const types = urlParams.getAll('type');
        types.forEach(type => {
            const checkbox = filterForm.querySelector(`input[name="type"][value="${type}"]`);
            if (checkbox) {
                checkbox.checked = true;
            }
        });
    }

    // Restore filter state when page loads
    restoreFilterState();
});
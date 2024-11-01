// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get references to elements
    const filterToggleBtn = document.getElementById('filterToggleBtn');
    const mobileFiltersModal = document.getElementById('mobileFiltersModal');
    const filterForm = document.getElementById('filterForm');
    const mobileFilterModalBody = document.getElementById('mobileFilterModalBody');
    const mobileApplyFiltersBtn = document.getElementById('mobileApplyFiltersBtn');

    // When filter button is clicked, show modal
    filterToggleBtn.addEventListener('click', function() {
        // Clone the filter form into the modal
        const filterFormClone = filterForm.cloneNode(true);
        mobileFilterModalBody.innerHTML = '';
        mobileFilterModalBody.appendChild(filterFormClone);

        // Show the modal
        const modal = new bootstrap.Modal(mobileFiltersModal);
        modal.show();
    });

    // When apply button is clicked
    mobileApplyFiltersBtn.addEventListener('click', function() {
        // Get the form from modal
        const modalForm = mobileFilterModalBody.querySelector('form');
        // Submit the form
        modalForm.submit();
    });
});
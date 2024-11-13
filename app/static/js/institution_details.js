document.addEventListener('DOMContentLoaded', function() {
    initializeSearch();
    initializeComparison();
    initializeSharing();
    initializeModals();
    initializeSorting();
});

function initializeSearch() {
    const searchInput = document.getElementById('courseSearch');
    const courseCards = document.querySelectorAll('.course-card');
    
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            
            courseCards.forEach(card => {
                const courseName = card.querySelector('.card-title').textContent.toLowerCase();
                const parentCol = card.closest('.col-md-6.col-lg-4');
                if (parentCol) {
                    parentCol.style.display = courseName.includes(searchTerm) ? 'block' : 'none';
                }
            });
        });
    }
}

function initializeComparison() {
    const compareBtn = document.getElementById('compareBtn');
    const checkboxes = document.querySelectorAll('.form-check-input');
    
    if (compareBtn) {
        compareBtn.addEventListener('click', function() {
            const selectedCourses = Array.from(checkboxes)
                .filter(cb => cb.checked)
                .map(cb => cb.value);
                
            if (selectedCourses.length < 2) {
                showError('Please select at least 2 courses to compare');
                return;
            }
            
            // Future implementation of course comparison
            console.log('Compare courses:', selectedCourses);
        });
    }
}

function initializeSharing() {
    const shareButtons = document.querySelectorAll('.share-btn');
    
    shareButtons.forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            const courseId = this.dataset.course;
            const url = window.location.href + '#course-' + courseId;
            
            try {
                if (navigator.share) {
                    await navigator.share({
                        title: 'Check out this course',
                        url: url
                    });
                } else {
                    await navigator.clipboard.writeText(url);
                    showSuccess('Link copied to clipboard!');
                }
            } catch (error) {
                console.error('Error sharing:', error);
                showError('Failed to share or copy link');
            }
        });
    });
}

function initializeModals() {
    const modalTriggers = document.querySelectorAll('[data-bs-toggle="modal"]');
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            const targetModalId = this.getAttribute('data-bs-target');
            const modalElement = document.querySelector(targetModalId);
            if (modalElement) {
                try {
                    const bsModal = new bootstrap.Modal(modalElement, {
                        backdrop: true,
                        keyboard: true,
                        focus: true
                    });
                    bsModal.show();
                } catch (error) {
                    console.error('Modal initialization error:', error);
                    showError('Failed to open course details');
                }
            }
        });
    });
}

function initializeSorting() {
    const sortDropdownItems = document.querySelectorAll('.dropdown-item[data-sort]');
    sortDropdownItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const sortBy = this.dataset.sort;
            sortCourses(sortBy);
        });
    });
}

function sortCourses(sortBy) {
    const coursesContainer = document.querySelector('.row');
    const courseCards = Array.from(document.querySelectorAll('.col-md-6.col-lg-4'));

    if (!coursesContainer || courseCards.length === 0) return;

    try {
        courseCards.sort((a, b) => {
            let aText, bText;
            if (sortBy === 'name') {
                aText = a.querySelector('.card-title').textContent.trim();
                bText = b.querySelector('.card-title').textContent.trim();
            } else {
                aText = a.querySelector('.badge:last-child').textContent.trim();
                bText = b.querySelector('.badge:last-child').textContent.trim();
            }
            return aText.localeCompare(bText);
        });

        // Clear and re-append sorted cards
        const parent = courseCards[0].parentNode;
        parent.innerHTML = '';
        courseCards.forEach(card => parent.appendChild(card));
    } catch (error) {
        console.error('Sorting error:', error);
        showError('Failed to sort courses');
    }
}

function showError(message) {
    showNotification(message, 'danger');
}

function showSuccess(message) {
    showNotification(message, 'success');
}

function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    
    const icon = type === 'danger' ? 'exclamation-circle' : 
                 type === 'success' ? 'check-circle' : 'info-circle';
    
    alertDiv.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${icon} me-2"></i>
            <div>${message}</div>
            <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 5000);
    }
} 
document.addEventListener('DOMContentLoaded', function() {
    // Course search functionality
    const searchInput = document.getElementById('courseSearch');
    const courseCards = document.querySelectorAll('.course-card');
    
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            
            courseCards.forEach(card => {
                const courseName = card.querySelector('.card-title').textContent.toLowerCase();
                const parentCol = card.closest('.col-md-6');
                if (parentCol) {
                    parentCol.style.display = courseName.includes(searchTerm) ? 'block' : 'none';
                }
            });
        });
    }
    
    // Course comparison
    const compareBtn = document.getElementById('compareBtn');
    const checkboxes = document.querySelectorAll('.form-check-input');
    
    if (compareBtn) {
        compareBtn.addEventListener('click', function() {
            const selectedCourses = Array.from(checkboxes)
                .filter(cb => cb.checked)
                .map(cb => cb.value);
                
            if (selectedCourses.length < 2) {
                alert('Please select at least 2 courses to compare');
                return;
            }
            
            // Implement comparison modal or navigation
            console.log('Compare courses:', selectedCourses);
        });
    }
    
    // Share functionality
    const shareButtons = document.querySelectorAll('.share-btn');
    
    shareButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const courseId = this.dataset.course;
            const url = window.location.href + '#course-' + courseId;
            
            if (navigator.share) {
                navigator.share({
                    title: 'Check out this course',
                    url: url
                }).catch(console.error);
            } else {
                // Fallback copy to clipboard
                navigator.clipboard.writeText(url)
                    .then(() => alert('Link copied to clipboard!'))
                    .catch(console.error);
            }
        });
    });

    // Initialize all modals
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modalEl => {
        if (modalEl) {
            new bootstrap.Modal(modalEl, {
                keyboard: true,
                backdrop: true,
                focus: true
            });
        }
    });

    // Sort functionality
    const sortDropdownItems = document.querySelectorAll('.dropdown-item[data-sort]');
    sortDropdownItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const sortBy = this.dataset.sort;
            sortCourses(sortBy);
        });
    });
});

function sortCourses(sortBy) {
    const coursesContainer = document.querySelector('.row');
    const courseCards = Array.from(document.querySelectorAll('.col-md-6'));

    courseCards.sort((a, b) => {
        const aText = a.querySelector(sortBy === 'name' ? '.card-title' : '.badge:last-child').textContent.trim();
        const bText = b.querySelector(sortBy === 'name' ? '.card-title' : '.badge:last-child').textContent.trim();
        return aText.localeCompare(bText);
    });

    courseCards.forEach(card => coursesContainer.appendChild(card));
} 
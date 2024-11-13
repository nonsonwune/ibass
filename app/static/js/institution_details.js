document.addEventListener('DOMContentLoaded', function() {
    // Get institution ID from data attribute
    const institutionId = document.body.dataset.institutionId;
    let selectedCourses = new Set();

    // Initialize all components
    initializeCompare();
    initializeSort();
    initializeRequirements();
    initializeComments();
    initializeShare();

    function initializeCompare() {
        const compareCheckboxes = document.querySelectorAll('.compare-checkbox');
        const compareBtn = document.getElementById('compareSelectedBtn');
        const selectedCountSpan = document.getElementById('selectedCount');

        if (!compareBtn || !selectedCountSpan) return;

        // Update compare button state
        function updateCompareButton() {
            const count = selectedCourses.size;
            selectedCountSpan.textContent = count;
            compareBtn.disabled = count < 2;
        }

        // Handle checkbox changes
        compareCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const courseId = this.value;
                if (this.checked) {
                    selectedCourses.add(courseId);
                } else {
                    selectedCourses.delete(courseId);
                }

                // Sync checkboxes with same course ID
                document.querySelectorAll(`.compare-checkbox[value="${courseId}"]`)
                    .forEach(cb => cb.checked = this.checked);

                updateCompareButton();
            });
        });

        // Handle compare button click
        compareBtn.addEventListener('click', function() {
            if (selectedCourses.size < 2) return;
            
            const courseIds = Array.from(selectedCourses).join(',');
            window.location.href = `/compare-courses?courses=${courseIds}`;
        });
    }

    function initializeSort() {
        const sortOptions = document.querySelectorAll('.sort-option');
        const coursesGrid = document.getElementById('allCoursesGrid');

        if (!coursesGrid) return;

        sortOptions.forEach(option => {
            option.addEventListener('click', function(e) {
                e.preventDefault();
                const sortBy = this.dataset.sort;
                const items = Array.from(coursesGrid.children);
                
                items.sort((a, b) => {
                    const aValue = a.dataset[sortBy].toLowerCase();
                    const bValue = b.dataset[sortBy].toLowerCase();
                    return aValue.localeCompare(bValue);
                });

                // Clear and re-append sorted items
                coursesGrid.innerHTML = '';
                items.forEach(item => coursesGrid.appendChild(item));
            });
        });
    }

    function initializeRequirements() {
        // Initialize all modals
        const requirementModals = document.querySelectorAll('.modal');
        requirementModals.forEach(modalElement => {
            new bootstrap.Modal(modalElement);
        });

        // Add click handlers for requirement buttons
        const requirementBtns = document.querySelectorAll('.view-requirements-btn');
        requirementBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const courseId = this.dataset.courseId;
                const modalId = `courseModal${courseId}`;
                const modalElement = document.getElementById(modalId);
                
                if (modalElement) {
                    const modal = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
                    modal.show();
                }
            });
        });
    }

    function initializeShare() {
        const shareBtns = document.querySelectorAll('.share-course-btn');
        
        shareBtns.forEach(btn => {
            btn.addEventListener('click', async function() {
                const courseId = this.dataset.courseId;
                const courseTitle = this.closest('.card').querySelector('.card-title').textContent;
                const shareUrl = `${window.location.origin}/course/${courseId}`;

                try {
                    if (navigator.share) {
                        await navigator.share({
                            title: courseTitle,
                            text: `Check out this course: ${courseTitle}`,
                            url: shareUrl
                        });
                    } else {
                        await navigator.clipboard.writeText(shareUrl);
                        showToast('Link copied to clipboard!', 'success');
                    }
                } catch (err) {
                    console.error('Error sharing:', err);
                    showToast('Failed to share course', 'error');
                }
            });
        });
    }

    function initializeComments() {
        const commentForm = document.getElementById('institutionCommentForm');
        const commentsContainer = document.getElementById('commentsContainer');

        if (!commentForm || !commentsContainer) return;

        // Load initial comments
        loadComments();

        // Handle comment submission
        commentForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const content = document.getElementById('institutionCommentContent').value;
            if (!content.trim()) return;

            try {
                const response = await fetch(`/api/institution/${institutionId}/comment`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': window.csrfToken
                    },
                    body: JSON.stringify({ content })
                });

                if (!response.ok) throw new Error('Failed to add comment');

                const data = await response.json();
                if (data.status === 'success') {
                    addCommentToDOM(data.comment);
                    commentForm.reset();
                    showToast('Comment added successfully', 'success');
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('Failed to add comment', 'error');
            }
        });
    }

    async function loadComments() {
        try {
            const response = await fetch(`/api/institution/${institutionId}/comments`);
            const data = await response.json();
            
            if (data.status === 'success') {
                const commentsContainer = document.getElementById('commentsContainer');
                commentsContainer.innerHTML = '';
                
                data.comments.forEach(comment => {
                    addCommentToDOM(comment);
                });
            }
        } catch (error) {
            console.error('Error loading comments:', error);
            showToast('Failed to load comments', 'error');
        }
    }

    // Helper Functions
    function showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer') || createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(container);
        return container;
    }

    function addCommentToDOM(comment) {
        const commentElement = document.createElement('div');
        commentElement.className = 'comment-card fade-in';
        commentElement.innerHTML = `
            <div class="p-3">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="d-flex align-items-center">
                        <div class="user-avatar me-2">
                            <i class="fas fa-user-circle text-primary"></i>
                        </div>
                        <div>
                            <h6 class="mb-0">
                                ${comment.author}
                                <span class="badge bg-primary-soft ms-1">${comment.author_score}</span>
                            </h6>
                            <small class="text-muted">${comment.date}</small>
                        </div>
                    </div>
                    <div class="comment-actions">
                        <button class="btn btn-sm btn-outline-primary vote-btn" data-vote="like" data-comment-id="${comment.id}">
                            <i class="fas fa-thumbs-up me-1"></i>${comment.likes}
                        </button>
                        <button class="btn btn-sm btn-outline-danger vote-btn" data-vote="dislike" data-comment-id="${comment.id}">
                            <i class="fas fa-thumbs-down me-1"></i>${comment.dislikes}
                        </button>
                    </div>
                </div>
                <p class="mb-0">${comment.content}</p>
            </div>
        `;
        
        // Add vote handlers
        const voteButtons = commentElement.querySelectorAll('.vote-btn');
        voteButtons.forEach(btn => {
            btn.addEventListener('click', handleVote);
        });
        
        const commentsContainer = document.getElementById('commentsContainer');
        commentsContainer.insertBefore(commentElement, commentsContainer.firstChild);
    }

    async function handleVote(e) {
        if (!window.isAuthenticated) {
            showToast('Please login to vote', 'warning');
            return;
        }

        const btn = e.currentTarget;
        const commentId = btn.dataset.commentId;
        const voteType = btn.dataset.vote;

        try {
            const response = await fetch(`/api/institution/comment/${commentId}/vote`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': window.csrfToken
                },
                body: JSON.stringify({ vote_type: voteType })
            });

            const data = await response.json();
            if (data.status === 'success') {
                updateVoteCounts(commentId, data.likes, data.dislikes);
                updateAuthorScore(commentId, data.author_score);
            }
        } catch (error) {
            console.error('Error voting:', error);
            showToast('Failed to register vote', 'error');
        }
    }
}); 
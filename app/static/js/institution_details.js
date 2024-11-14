// Main module for institution details
const InstitutionDetails = {
    // State
    state: {
        institutionId: null,
        isAuthenticated: window.isAuthenticated || false,
        csrfToken: window.csrfToken || null
    },

    // Initialize all functionality
    init() {
        console.log('Initializing InstitutionDetails module'); // Debug log
        this.state.institutionId = this.getInstitutionIdFromUrl();
        console.log('Institution ID:', this.state.institutionId); // Debug log
        
        this.commentSystem.init();
        this.votingSystem.init();
        this.loadComments();
        
        if (this.state.isAuthenticated) {
            console.log('User is authenticated, fetching votes'); // Debug log
            this.votingSystem.fetchUserVotes();
        }
    },

    // Get institution ID from URL
    getInstitutionIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        return pathParts[pathParts.length - 1];
    },

    // Comment System Module
    commentSystem: {
        elements: {
            form: null,
            textarea: null,
            charCount: null,
            container: null
        },

        init() {
            console.log('Initializing comment system'); // Debug log
            this.initializeElements();
            this.loadComments();
            this.bindEvents();
        },

        initializeElements() {
            console.log('Initializing comment elements'); // Debug log
            this.elements.form = document.getElementById('commentForm');
            this.elements.textarea = document.getElementById('institutionComment');
            this.elements.charCount = document.getElementById('charCount');
            this.elements.container = document.getElementById('commentsContainer');
            
            // Log element initialization status
            console.log('Form element found:', !!this.elements.form);
            console.log('Textarea element found:', !!this.elements.textarea);
            console.log('CharCount element found:', !!this.elements.charCount);
            console.log('Container element found:', !!this.elements.container);
        },

        bindEvents() {
            console.log('Binding comment system events'); // Debug log
            
            if (this.elements.textarea && this.elements.charCount) {
                this.elements.textarea.addEventListener('input', this.handleCharCount.bind(this));
                console.log('Bound textarea input event');
            }

            if (this.elements.form) {
                this.elements.form.addEventListener('submit', (e) => {
                    console.log('Form submit event triggered'); // Debug log
                    this.handleSubmit(e);
                });
                console.log('Bound form submit event');
            } else {
                console.error('Comment form not found!');
            }
        },

        handleCharCount(e) {
            const remaining = 200 - e.target.value.length;
            this.elements.charCount.textContent = `${remaining} remaining`;
            this.elements.charCount.classList.toggle('text-danger', remaining < 20);
        },

        async handleSubmit(e) {
            try {
                console.log('Form submission started');
                e.preventDefault();
                
                // Get and validate csrf token
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
                if (!csrfToken) {
                    throw new Error('CSRF token not found');
                }
                console.log('CSRF Token:', 'Present');
                
                // Get and validate institution ID
                const institutionId = InstitutionDetails.state.institutionId;
                if (!institutionId) {
                    throw new Error('Institution ID not found');
                }
                console.log('Institution ID:', institutionId);
        
                // Get and validate textarea content
                const textarea = this.elements.textarea;
                if (!textarea) {
                    throw new Error('Comment textarea not found');
                }
        
                const content = textarea.value.trim();
                console.log('Comment content:', content);
        
                // Validate content
                if (!content) {
                    console.log('Empty comment detected');
                    textarea.classList.add('is-invalid');
                    UIHelper.showToast('Please enter a comment', 'warning');
                    return;
                }
        
                // Get and prepare submit button
                const submitButton = e.target.querySelector('button[type="submit"]');
                if (!submitButton) {
                    throw new Error('Submit button not found');
                }
                const originalButtonText = submitButton.innerHTML;
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Posting...';
        
                // Prepare request payload
                const payload = { content };
                console.log('Sending request to:', `/api/institution/${institutionId}/comment`);
                console.log('With payload:', payload);
        
                // Make API request
                const response = await fetch(`/api/institution/${institutionId}/comment`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken
                    },
                    body: JSON.stringify(payload),
                    credentials: 'same-origin'
                });
        
                console.log('Response status:', response.status);
                
                // Parse response
                const data = await response.json();
                console.log('Response data:', data);
        
                // Handle success
                if (response.ok && data.status === 'success') {
                    // Add comment to DOM
                    this.addCommentToDOM(data.comment);
                    
                    // Reset form
                    textarea.value = '';
                    textarea.classList.remove('is-invalid');
                    
                    // Close modal if present
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addCommentModal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Show success message and clean up
                    UIHelper.showToast('Comment added successfully', 'success');
                    this.removeEmptyState();
                    
                } else {
                    // Handle API error
                    throw new Error(data.message || 'Server returned error response');
                }
        
            } catch (error) {
                // Log and display error
                console.error('Comment submission error:', error);
                UIHelper.showToast(error.message || 'Failed to add comment', 'error');
                
            } finally {
                // Reset submit button
                const submitButton = e.target.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Post Comment';
                }
            }
        },

        async loadComments() {
            console.log('Loading comments for institution:', InstitutionDetails.state.institutionId);
            try {
                const response = await fetch(`/api/institution/${InstitutionDetails.state.institutionId}/comments`);
                console.log('Comments API Response:', response.status);
                const data = await response.json();
                console.log('Comments Data:', data);
                
                if (data.status === 'success') {
                    this.elements.container.innerHTML = '';
                    
                    if (!data.comments || data.comments.length === 0) {
                        console.log('No comments found, showing empty state');
                        this.showEmptyState();
                        return;
                    }
        
                    console.log(`Rendering ${data.comments.length} comments`);
                    data.comments.forEach(comment => {
                        console.log('Rendering comment:', comment);
                        this.addCommentToDOM(comment);
                    });
                }
            } catch (error) {
                console.error('Error loading comments:', error);
                UIHelper.showToast('Failed to load comments', 'error');
                this.showEmptyState();
            }
        },

        addCommentToDOM(comment) {
            console.log('Adding comment to DOM:', comment); // Debug log
            const commentElement = document.createElement('div');
            commentElement.className = 'comment-card fade-in';
            commentElement.dataset.commentId = comment.id;
            
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
                            <button class="btn btn-sm btn-outline-primary vote-btn" 
                                    data-vote="like" 
                                    data-comment-id="${comment.id}">
                                <i class="fas fa-thumbs-up me-1"></i>${comment.likes}
                            </button>
                            <button class="btn btn-sm btn-outline-danger vote-btn" 
                                    data-vote="dislike" 
                                    data-comment-id="${comment.id}">
                                <i class="fas fa-thumbs-down me-1"></i>${comment.dislikes}
                            </button>
                        </div>
                    </div>
                    <p class="mb-0">${comment.content}</p>
                </div>
            `;
            
            this.elements.container.insertBefore(commentElement, this.elements.container.firstChild);
            console.log('Comment added to DOM successfully'); // Debug log
        },

        showEmptyState() {
            console.log('Showing empty state'); // Debug log
            this.elements.container.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-comments text-muted fa-3x mb-3"></i>
                    <p class="text-muted">No comments yet. Be the first to share your thoughts!</p>
                </div>
            `;
        },

        removeEmptyState() {
            const emptyState = this.elements.container.querySelector('.text-center');
            if (emptyState) {
                console.log('Removing empty state'); // Debug log
                emptyState.remove();
            }
        }
    },

    // Voting System Module
    votingSystem: {
        init() {
            document.addEventListener('click', this.handleVoteClick.bind(this));
        },

        async handleVoteClick(e) {
            const voteBtn = e.target.closest('.vote-btn');
            if (!voteBtn) return;

            if (!InstitutionDetails.state.isAuthenticated) {
                UIHelper.showToast('Please login to vote', 'warning');
                return;
            }

            const commentId = voteBtn.dataset.commentId;
            const voteType = voteBtn.dataset.vote;

            try {
                const response = await fetch(`/api/institution/comment/${commentId}/vote`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': InstitutionDetails.state.csrfToken
                    },
                    body: JSON.stringify({ vote_type: voteType })
                });

                const data = await response.json();
                if (data.status === 'success') {
                    this.updateVoteCounts(commentId, data.likes, data.dislikes);
                    this.updateAuthorScore(commentId, data.author_score);
                }
            } catch (error) {
                console.error('Error voting:', error);
                UIHelper.showToast('Failed to register vote', 'error');
            }
        },

        async fetchUserVotes() {
            try {
                const response = await fetch('/api/user_votes');
                const data = await response.json();
                if (data) {
                    this.applyUserVotes(data);
                }
            } catch (error) {
                console.error('Error fetching user votes:', error);
            }
        },

        applyUserVotes(votes) {
            if (!votes) return;
            document.querySelectorAll('.vote-btn').forEach(button => {
                const commentId = button.dataset.commentId;
                const voteType = button.dataset.vote;

                button.classList.remove('active');
                if (votes[commentId] === voteType) {
                    button.classList.add('active');
                }
            });
        },

        updateVoteCounts(commentId, likes, dislikes) {
            const comment = document.querySelector(`[data-comment-id="${commentId}"]`);
            if (comment) {
                const likeBtn = comment.querySelector('[data-vote="like"]');
                const dislikeBtn = comment.querySelector('[data-vote="dislike"]');
                
                if (likeBtn) likeBtn.innerHTML = `<i class="fas fa-thumbs-up me-1"></i>${likes}`;
                if (dislikeBtn) dislikeBtn.innerHTML = `<i class="fas fa-thumbs-down me-1"></i>${dislikes}`;
            }
        },

        updateAuthorScore(commentId, newScore) {
            const comment = document.querySelector(`[data-comment-id="${commentId}"]`);
            if (comment) {
                const scoreElement = comment.querySelector('.badge');
                if (scoreElement) {
                    scoreElement.textContent = newScore;
                }
            }
        }
    },

    loadComments() {
        this.commentSystem.loadComments();
    }
};

// UI Helper Module
const UIHelper = {
    showToast(message, type = 'info') {
        const container = this.getToastContainer();
        
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

        container.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    },

    getToastContainer() {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(container);
        }
        return container;
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing InstitutionDetails'); // Debug log
    InstitutionDetails.init();
});

// Add comment handling
document.getElementById('commentForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const commentText = document.getElementById('institutionComment').value;
    const universityId = window.location.pathname.split('/').pop();
    
    try {
        const response = await fetch('/add_comment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            },
            body: JSON.stringify({
                content: commentText,
                university_id: universityId
            })
        });

        if (response.ok) {
            // Refresh comments or add new comment to DOM
            location.reload();
        } else {
            showToast('Error posting comment', 'danger');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error posting comment', 'danger');
    }
});
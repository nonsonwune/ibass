// Main module for institution details
const InstitutionDetails = {
    // State
    state: {
        institutionId: null,
        isAuthenticated: window.isAuthenticated || false,
        csrfToken: document.querySelector('meta[name="csrf-token"]')?.content
    },

    // Initialize all functionality
    init() {
        console.log('Initializing InstitutionDetails module');
        this.state.institutionId = window.institutionId;
        
        this.initializeCharCount();
        this.votingSystem.init();
    },

    // Initialize character count
    initializeCharCount() {
        const textarea = document.getElementById('institutionComment');
        const charCount = document.getElementById('charCount');
        
        if (textarea && charCount) {
            textarea.addEventListener('input', function() {
                const remaining = 200 - this.value.length;
                charCount.textContent = `${remaining} remaining`;
                charCount.classList.toggle('text-danger', remaining < 20);
            });
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
            const voteType = voteBtn.dataset.voteType;

            try {
                const response = await fetch(`/api/institution/comments/${commentId}/vote`, {
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
                }
            } catch (error) {
                console.error('Error voting:', error);
                UIHelper.showToast('Failed to register vote', 'error');
            }
        },

        updateVoteCounts(commentId, likes, dislikes) {
            const comment = document.querySelector(`#comment-${commentId}`);
            if (comment) {
                comment.querySelector('.like-count').textContent = `(${likes})`;
                comment.querySelector('.dislike-count').textContent = `(${dislikes})`;
            }
        }
    }
};

// UI Helper Module
const UIHelper = {
    showToast(message, type = 'info') {
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
        
        const container = document.getElementById('toastContainer');
        container.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing InstitutionDetails');
    InstitutionDetails.init();
});

document.addEventListener('DOMContentLoaded', function() {
    // Vote functionality
    document.querySelectorAll('.vote-btn').forEach(button => {
        button.addEventListener('click', function() {
            if (!window.isAuthenticated) {
                showToast('Please log in to vote', 'warning');
                return;
            }

            const commentId = this.dataset.commentId;
            const voteType = this.dataset.voteType;

            fetch(`/api/institution_comment/${commentId}/vote`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken
                },
                body: JSON.stringify({ vote_type: voteType })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update vote counts
                    const commentCard = this.closest('.comment-card');
                    commentCard.querySelector('.like-count').textContent = `(${data.likes})`;
                    commentCard.querySelector('.dislike-count').textContent = `(${data.dislikes})`;
                    
                    // Update user score if shown
                    const userScoreElement = document.querySelector(`.user-score[data-user-id="${data.user_id}"]`);
                    if (userScoreElement) {
                        userScoreElement.textContent = data.user_score;
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error processing vote', 'error');
            });
        });
    });

    // Reply functionality
    document.querySelectorAll('.reply-btn').forEach(button => {
        button.addEventListener('click', function() {
            if (!window.isAuthenticated) {
                showToast('Please log in to reply', 'warning');
                return;
            }

            const commentId = this.dataset.commentId;
            const institutionId = window.institutionId;
            const commentContent = this.closest('.comment-card').querySelector('.comment-content').textContent;
            
            // Show reply modal
            const replyModal = new bootstrap.Modal(document.getElementById('replyModal'));
            document.querySelector('.parent-comment').textContent = commentContent;
            
            // Handle reply submission
            document.querySelector('.submit-reply').onclick = function() {
                const content = document.querySelector('.reply-textarea').value;
                
                fetch('/api/institution_comment/reply', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.csrfToken
                    },
                    body: JSON.stringify({
                        content: content,
                        parent_id: commentId,
                        institution_id: institutionId
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Add reply to the UI
                        const repliesContainer = document.querySelector(`#replies-${commentId}`);
                        const replyHTML = createReplyHTML(data.reply);
                        repliesContainer.insertAdjacentHTML('beforeend', replyHTML);
                        
                        replyModal.hide();
                        showToast('Reply added successfully', 'success');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast('Error adding reply', 'error');
                });
            };
            
            replyModal.show();
        });
    });

    // Delete functionality
    document.querySelectorAll('.delete-comment').forEach(button => {
        button.addEventListener('click', function() {
            if (confirm('Are you sure you want to delete this comment?')) {
                const commentId = this.dataset.commentId;
                
                fetch(`/api/institution_comment/${commentId}/delete`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.csrfToken
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.closest('.comment-card').remove();
                        showToast('Comment deleted successfully', 'success');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast('Error deleting comment', 'error');
                });
            }
        });
    });
});

function createReplyHTML(reply) {
    return `
        <div class="reply-card animate__animated animate__fadeIn" id="comment-${reply.id}">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div class="d-flex align-items-center">
                    <div class="user-avatar me-2">
                        <i class="fas fa-user-circle text-primary"></i>
                    </div>
                    <div>
                        <h6 class="mb-0 ${reply.is_admin ? 'admin-username' : ''}">
                            ${reply.author}
                            <span class="badge bg-primary-soft ms-1 user-score" data-user-id="${reply.user_id}">
                                ${reply.author_score}
                            </span>
                        </h6>
                        <small class="text-muted">${reply.date}</small>
                    </div>
                </div>
            </div>
            <div class="reply-content mb-2">
                <p class="mb-0">${reply.content}</p>
            </div>
            <div class="d-flex justify-content-between align-items-center">
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-sm btn-outline-primary vote-btn" 
                            data-comment-id="${reply.id}" 
                            data-vote-type="like">
                        <i class="fas fa-thumbs-up me-1"></i>
                        <span class="like-count">(${reply.likes})</span>
                    </button>
                    <button class="btn btn-sm btn-outline-danger vote-btn" 
                            data-comment-id="${reply.id}" 
                            data-vote-type="dislike">
                        <i class="fas fa-thumbs-down me-1"></i>
                        <span class="dislike-count">(${reply.dislikes})</span>
                    </button>
                </div>
                ${reply.user_id === currentUserId || isAdmin ? `
                    <button class="btn btn-sm btn-danger delete-comment" 
                            data-comment-id="${reply.id}">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                ` : ''}
            </div>
        </div>
    `;
}

function showToast(message, type) {
    const toastContainer = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.classList.add('toast', `bg-${type}`, 'text-white');
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">Notification</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;

    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}
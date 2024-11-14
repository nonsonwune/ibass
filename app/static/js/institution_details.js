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
        this.initializeVoting();
        this.initializeReplySystem();
        if (this.state.isAuthenticated) {
            this.fetchUserVotes();
        }
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

    initializeVoting() {
        document.querySelectorAll('.vote-btn').forEach(button => {
            button.addEventListener('click', async (e) => {
                e.preventDefault();
                if (!this.state.isAuthenticated) {
                    window.location.href = '/auth/login';
                    return;
                }

                const commentId = button.dataset.commentId;
                const voteType = button.dataset.voteType;
                const commentCard = button.closest('.comment-card');
                
                // Disable all vote buttons in this comment card
                const voteButtons = commentCard.querySelectorAll('.vote-btn');
                voteButtons.forEach(btn => btn.disabled = true);

                try {
                    const response = await fetch(`/api/institution/comment/${commentId}/vote`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': this.state.csrfToken
                        },
                        body: JSON.stringify({ vote_type: voteType })
                    });

                    const data = await response.json();
                    if (data.status === 'success') {
                        // Update vote counts
                        const likeCount = commentCard.querySelector('.like-count');
                        const dislikeCount = commentCard.querySelector('.dislike-count');
                        if (likeCount) likeCount.textContent = `(${data.likes})`;
                        if (dislikeCount) dislikeCount.textContent = `(${data.dislikes})`;

                        // Update user score if provided
                        if (data.author_score) {
                            const userScores = document.querySelectorAll(
                                `.user-score[data-user-id="${data.user_id}"]`
                            );
                            userScores.forEach(score => score.textContent = data.author_score);
                        }

                        // Update button states
                        voteButtons.forEach(btn => {
                            btn.classList.remove('active');
                            if (btn.dataset.voteType === voteType) {
                                btn.classList.add('active');
                            }
                        });

                        UIHelper.showToast('Vote recorded successfully', 'success');
                    }
                } catch (error) {
                    console.error('Error voting:', error);
                    UIHelper.showToast('Failed to record vote', 'danger');
                } finally {
                    voteButtons.forEach(btn => btn.disabled = false);
                }
            });
        });
    },

    async fetchUserVotes() {
        try {
            const response = await fetch('/api/user_votes', {
                headers: { 'X-CSRF-Token': this.state.csrfToken }
            });
            const data = await response.json();
            this.applyUserVotes(data);
        } catch (error) {
            console.error('Error fetching user votes:', error);
        }
    },

    applyUserVotes(votes) {
        document.querySelectorAll('.vote-btn').forEach(button => {
            const commentId = button.dataset.commentId;
            const voteType = button.dataset.voteType;
            button.classList.toggle('active', votes[commentId] === voteType);
        });
    },

    initializeReplySystem() {
        const replyModal = document.getElementById('replyModal');
        if (!replyModal) return;

        // Handle reply button clicks
        document.querySelectorAll('.reply-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                if (!this.state.isAuthenticated) {
                    window.location.href = '/auth/login';
                    return;
                }

                const commentId = button.dataset.commentId;
                const commentCard = button.closest('.comment-card');
                const content = commentCard.querySelector('.comment-content').textContent.trim();

                const modal = new bootstrap.Modal(replyModal);
                const parentComment = replyModal.querySelector('.parent-comment');
                const replyTextarea = replyModal.querySelector('.reply-textarea');
                const submitButton = replyModal.querySelector('.submit-reply');

                parentComment.textContent = content;
                replyTextarea.value = '';
                submitButton.dataset.parentId = commentId;

                modal.show();
            });
        });

        // Handle reply submission
        const submitReplyBtn = replyModal.querySelector('.submit-reply');
        submitReplyBtn.addEventListener('click', async () => {
            const textarea = replyModal.querySelector('.reply-textarea');
            const content = textarea.value.trim();
            const parentId = submitReplyBtn.dataset.parentId;

            if (!content) {
                UIHelper.showToast('Reply cannot be empty', 'warning');
                return;
            }

            submitReplyBtn.disabled = true;
            submitReplyBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Posting...';

            try {
                const response = await fetch('/api/institution/comment/reply', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': this.state.csrfToken
                    },
                    body: JSON.stringify({
                        parent_id: parentId,
                        content: content,
                        institution_id: this.state.institutionId
                    })
                });

                const data = await response.json();
                if (data.status === 'success') {
                    location.reload(); // Reload to show new reply
                } else {
                    throw new Error(data.message || 'Failed to post reply');
                }
            } catch (error) {
                console.error('Error posting reply:', error);
                UIHelper.showToast('Failed to post reply', 'danger');
            } finally {
                submitReplyBtn.disabled = false;
                submitReplyBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Post Reply';
            }
        });

        // Handle character count for replies
        const replyTextarea = replyModal.querySelector('.reply-textarea');
        const charCount = replyModal.querySelector('.reply-char-count');
        if (replyTextarea && charCount) {
            replyTextarea.addEventListener('input', function() {
                const remaining = 200 - this.value.length;
                charCount.textContent = remaining;
                charCount.classList.toggle('text-danger', remaining < 20);
            });
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
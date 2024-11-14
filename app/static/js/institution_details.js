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
// Main module for institution details
const InstitutionDetails = {
    // State
    state: {
        institutionId: null,
        isAuthenticated: window.isAuthenticated === "true",
        csrfToken: document.querySelector('meta[name="csrf-token"]')?.content
    },

    // Initialize all functionality
    init() {
        this.state.institutionId = window.institutionId;
        this.initializeComments();
        this.initializeBookmarks();
        this.initializeCharCount();
    },

    // Initialize comments functionality
    initializeComments() {
        // Add comment button
        const addCommentBtn = document.querySelector('[data-bs-target="#addCommentModal"]');
        if (addCommentBtn) {
            addCommentBtn.addEventListener('click', (e) => {
                if (!this.state.isAuthenticated) {
                    e.preventDefault();
                    this.showAuthenticationPrompt('comment');
                    return false;
                }
            });
        }

        // Reply buttons
        document.querySelectorAll('.reply-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                if (!this.state.isAuthenticated) {
                    e.preventDefault();
                    this.showAuthenticationPrompt('reply');
                    return false;
                }
            });
        });

        // Vote buttons
        document.querySelectorAll('.vote-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                if (!this.state.isAuthenticated) {
                    e.preventDefault();
                    this.showAuthenticationPrompt('vote');
                    return false;
                }
                const commentId = button.dataset.commentId;
                const voteType = button.dataset.voteType;
                this.handleVote(commentId, voteType);
            });
        });
    },

    // Initialize bookmarks functionality
    initializeBookmarks() {
        const bookmarkBtn = document.querySelector('.bookmark-btn');
        if (bookmarkBtn) {
            bookmarkBtn.addEventListener('click', (e) => {
                if (!this.state.isAuthenticated) {
                    e.preventDefault();
                    this.showAuthenticationPrompt('bookmark');
                    return false;
                }
                this.handleBookmark();
            });
        }
    },

    // Show authentication prompt
    showAuthenticationPrompt(action) {
        const messages = {
            comment: 'Please log in to add a comment',
            reply: 'Please log in to reply',
            vote: 'Please log in to vote',
            bookmark: 'Please log in to bookmark this institution'
        };

        UIHelper.showToast(messages[action], 'warning');
        setTimeout(() => {
            window.location.href = '/auth/login';
        }, 1500);
    },

    // Handle voting
    async handleVote(commentId, voteType) {
        try {
            const response = await fetch(`/api/institution_comment/${commentId}/vote`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.state.csrfToken
                },
                body: JSON.stringify({ vote_type: voteType })
            });

            const data = await response.json();
            if (data.success) {
                this.updateVoteCounts(commentId, data);
                UIHelper.showToast('Vote recorded successfully', 'success');
            }
        } catch (error) {
            console.error('Error voting:', error);
            UIHelper.showToast('Failed to record vote', 'error');
        }
    },

    // Handle bookmark
    async handleBookmark() {
        try {
            const response = await fetch('/api/bookmark', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.state.csrfToken
                },
                body: JSON.stringify({ 
                    university_id: this.state.institutionId 
                })
            });

            const data = await response.json();
            if (data.success) {
                UIHelper.showToast(data.message, 'success');
                this.updateBookmarkButton(true);
            }
        } catch (error) {
            console.error('Error bookmarking:', error);
            UIHelper.showToast('Failed to bookmark institution', 'error');
        }
    },

    // Update vote counts in UI
    updateVoteCounts(commentId, data) {
        const commentElement = document.querySelector(`#comment-${commentId}`);
        if (commentElement) {
            const likeCount = commentElement.querySelector('.like-count');
            const dislikeCount = commentElement.querySelector('.dislike-count');
            if (likeCount) likeCount.textContent = `(${data.likes})`;
            if (dislikeCount) dislikeCount.textContent = `(${data.dislikes})`;
        }
    },

    // Update bookmark button state
    updateBookmarkButton(isBookmarked) {
        const bookmarkBtn = document.querySelector('.bookmark-btn');
        if (bookmarkBtn) {
            bookmarkBtn.innerHTML = isBookmarked ? 
                '<i class="fas fa-bookmark"></i> Bookmarked' :
                '<i class="far fa-bookmark"></i> Bookmark';
            bookmarkBtn.classList.toggle('btn-primary', !isBookmarked);
            bookmarkBtn.classList.toggle('btn-success', isBookmarked);
        }
    },

    // Initialize character count for comment textarea
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
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    InstitutionDetails.init();
});

document.addEventListener('DOMContentLoaded', function() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
    
    // Handle voting
    document.querySelectorAll('.vote-btn').forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            const commentId = this.dataset.commentId;
            const voteType = this.dataset.voteType;
            
            try {
                const response = await fetch(`/api/comment/${commentId}/vote`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': csrfToken
                    },
                    body: JSON.stringify({ vote_type: voteType })
                });
                
                const data = await response.json();
                if (data.success) {
                    const commentCard = document.querySelector(`#comment-${commentId}`);
                    commentCard.querySelector('.like-count').textContent = `(${data.likes})`;
                    commentCard.querySelector('.dislike-count').textContent = `(${data.dislikes})`;
                    showToast('Vote recorded successfully', 'success');
                } else {
                    showToast(data.message || 'Error voting on comment', 'danger');
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('Error voting on comment', 'danger');
            }
        });
    });
    
    // Handle comment deletion
    document.querySelectorAll('.delete-comment').forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            if (!confirm('Are you sure you want to delete this comment?')) return;
            
            const commentId = this.dataset.commentId;
            
            try {
                const response = await fetch(`/api/comment/${commentId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': csrfToken
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                if (data.success) {
                    const commentCard = document.querySelector(`#comment-${commentId}`);
                    if (commentCard) {
                        commentCard.remove();
                        showToast('Comment deleted successfully', 'success');
                    }
                } else {
                    showToast(data.message || 'Error deleting comment', 'danger');
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('Error deleting comment', 'danger');
            }
        });
    });

    // Handle replies
    document.querySelectorAll('.reply-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.dataset.commentId;
            const commentContent = document.querySelector(`#comment-${commentId} .comment-content`).textContent;
            
            // Populate reply modal
            document.querySelector('#replyModal .parent-comment').textContent = commentContent;
            document.querySelector('#replyModal .submit-reply').dataset.parentId = commentId;
            
            // Show modal
            new bootstrap.Modal(document.getElementById('replyModal')).show();
        });
    });

    // Handle reply submission
    document.querySelector('.submit-reply')?.addEventListener('click', async function() {
        const parentId = this.dataset.parentId;
        const content = document.querySelector('.reply-textarea').value;
        
        if (!content.trim()) {
            showToast('Reply cannot be empty', 'warning');
            return;
        }
        
        try {
            const response = await fetch(`/api/comment/${parentId}/reply`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken
                },
                body: JSON.stringify({ content: content })
            });
            
            const data = await response.json();
            if (data.success) {
                // Add reply to UI
                const replyHtml = createReplyElement(data.reply);
                const repliesContainer = document.querySelector(`#replies-${parentId}`);
                repliesContainer.insertAdjacentHTML('beforeend', replyHtml);
                
                // Close modal and clear textarea
                bootstrap.Modal.getInstance(document.getElementById('replyModal')).hide();
                document.querySelector('.reply-textarea').value = '';
                
                showToast('Reply added successfully', 'success');
            } else {
                showToast(data.message || 'Error adding reply', 'danger');
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Error adding reply', 'danger');
        }
    });

    function createReplyElement(reply) {
        return `
            <div class="reply-card" id="comment-${reply.id}">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="d-flex align-items-center">
                        <div class="user-avatar me-2">
                            <i class="fas fa-user-circle text-primary"></i>
                        </div>
                        <div>
                            <h6 class="mb-0">${reply.author}</h6>
                            <small class="text-muted">${reply.date_posted}</small>
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
                </div>
            </div>
        `;
    }
});
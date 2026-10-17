function getCsrfToken() {
    const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (tokenInput && tokenInput.value) {
        return tokenInput.value;
    }
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

const createForm = document.getElementById('create-form');

if (createForm) {
    createForm.addEventListener('submit', handleCreatePost);
}

function checkServerPort() {
    const errorDiv = document.getElementById('form-error');
    if (window.location.port && window.location.port !== '8000') {
        if (errorDiv) {
            errorDiv.innerHTML = `⚠️ <strong>Note:</strong> You are currently viewing this page through Live Server on <strong>port ${window.location.port}</strong>.<br><br>The Django backend is running on <strong>port 8000</strong>. Please open <a href="http://127.0.0.1:8000/create/" style="color: #0d47a1; text-decoration: underline; font-weight: bold;">http://127.0.0.1:8000/create/</a> to publish posts to the database.`;
            errorDiv.style.display = 'block';
        }
    }
}

async function handleCreatePost(e) {
    e.preventDefault();

    const titleInput = document.getElementById('post-title');
    const contentInput = document.getElementById('post-content');
    const errorDiv = document.getElementById('form-error');
    const submitBtn = createForm.querySelector('button[type="submit"]');

    if (window.location.port && window.location.port !== '8000') {
        if (errorDiv) {
            errorDiv.innerHTML = `⚠️ <strong>Note:</strong> You are on port ${window.location.port} (Live Server). Please open <a href="http://127.0.0.1:8000/create/" style="color:#0d47a1;text-decoration:underline;font-weight:bold;">http://127.0.0.1:8000/create/</a> to publish.`;
            errorDiv.style.display = 'block';
        }
        return;
    }

    const title = titleInput ? titleInput.value.trim() : '';
    const content = contentInput ? contentInput.value.trim() : '';

    if (!title || !content) {
        if (errorDiv) {
            errorDiv.textContent = 'Please fill in both title and content.';
            errorDiv.style.display = 'block';
        }
        return;
    }

    if (errorDiv) {
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Publishing...';
    }

    try {
        const csrfToken = getCsrfToken();
        const response = await fetch('/api/posts/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ title, content })
        });

        const data = await response.json().catch(() => ({}));

        // 401 means the user is not logged in — redirect to login page
        if (response.status === 401) {
            window.location.href = '/login/?next=/create/';
            return;
        }

        if (!response.ok) {
            throw new Error(data.error || `Server returned error (${response.status} ${response.statusText}).`);
        }

        createForm.reset();
        localStorage.removeItem('posts');

        window.location.href = '/#explore';
    } catch (err) {
        if (errorDiv) {
            errorDiv.textContent = err.message || 'Network error. Could not connect to the server.';
            errorDiv.style.display = 'block';
        }
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Publish';
        }
    }
}

async function loadPosts() {
    const exploreSection = document.getElementById('explore');
    if (!exploreSection) return;

    try {
        const response = await fetch('/api/posts/');
        if (!response.ok) {
            console.error('Failed to load posts from server.');
            return;
        }

        const data = await response.json();
        const posts = data.posts || [];

        let storedPostsContainer = document.getElementById('stored-posts-container');

        if (!storedPostsContainer && posts.length > 0) {
            storedPostsContainer = document.createElement('div');
            storedPostsContainer.id = 'stored-posts-container';
            const heading = exploreSection.querySelector('h2');
            if (heading) {
                heading.insertAdjacentElement('afterend', storedPostsContainer);
            } else {
                exploreSection.prepend(storedPostsContainer);
            }
        }

        if (storedPostsContainer && posts.length > 0) {
            storedPostsContainer.innerHTML = '';
            const csrfToken = getCsrfToken();

            posts.forEach(post => {
                const article = document.createElement('article');
                article.className = 'explore-post-card';
                article.dataset.postId = post.id;

                const detailUrl = post.detail_url || `/posts/${post.id}/`;

                // Post Title Link
                const title = document.createElement('h3');
                const titleLink = document.createElement('a');
                titleLink.href = detailUrl;
                titleLink.className = 'post-title-link';
                titleLink.textContent = post.title;
                title.appendChild(titleLink);

                // Content Preview
                const content = document.createElement('p');
                content.className = 'post-content-preview';
                // Preview ~40 words
                const words = post.content ? post.content.split(/\s+/) : [];
                content.textContent = words.length > 40 ? words.slice(0, 40).join(' ') + '…' : post.content;

                // Build author link if profile URL is available
                const meta = document.createElement('p');
                meta.className = 'post-meta';

                const date = new Date(post.created_at);
                const formattedDate = !isNaN(date.getTime())
                    ? date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                    })
                    : '';

                if (post.author && post.author_profile_url) {
                    const authorLink = document.createElement('a');
                    authorLink.href = post.author_profile_url;
                    authorLink.textContent = post.author;
                    meta.append('by ');
                    meta.appendChild(authorLink);
                    if (formattedDate) {
                        meta.append(' · ' + formattedDate);
                    }
                } else {
                    const authorName = post.author || 'Unknown author';
                    meta.append(`by ${authorName}`);
                    if (formattedDate) {
                        meta.append(' · ' + formattedDate);
                    }
                }

                // Social Actions Bar
                const actions = document.createElement('div');
                actions.className = 'post-card-actions';

                // Like Form/Button
                const likeForm = document.createElement('form');
                likeForm.method = 'post';
                likeForm.action = `/posts/${post.id}/like/`;
                likeForm.className = 'like-form inline-form';
                likeForm.dataset.postId = post.id;

                const likeBtn = document.createElement('button');
                likeBtn.type = 'submit';
                likeBtn.className = 'like-btn' + (post.has_liked ? ' liked' : '');
                likeBtn.setAttribute('aria-label', 'Like post');
                likeBtn.innerHTML = `
                    <span class="like-icon">${post.has_liked ? '♥' : '♡'}</span>
                    <span class="like-text">${post.has_liked ? 'Liked' : 'Like'}</span>
                    <span class="like-count">(${post.likes_count || 0})</span>
                `;
                likeForm.appendChild(likeBtn);

                // Comment Count Link
                const commentLink = document.createElement('a');
                commentLink.href = `${detailUrl}#comments`;
                commentLink.className = 'action-item comment-action-link';
                const commentsCount = post.comments_count || 0;
                commentLink.innerHTML = `
                    <span class="comment-icon">💬</span>
                    <span class="comment-count-text">${commentsCount} comment${commentsCount === 1 ? '' : 's'}</span>
                `;

                // Share Button
                const shareBtn = document.createElement('button');
                shareBtn.type = 'button';
                shareBtn.className = 'share-btn';
                shareBtn.dataset.shareTitle = post.title;
                shareBtn.dataset.shareUrl = `${window.location.origin}${detailUrl}`;
                shareBtn.innerHTML = `<span class="share-icon">↗</span><span class="share-text">Share</span>`;

                const shareToast = document.createElement('span');
                shareToast.className = 'share-toast';
                shareToast.style.display = 'none';
                shareToast.textContent = 'Link copied!';

                actions.appendChild(likeForm);
                actions.appendChild(commentLink);
                actions.appendChild(shareBtn);
                actions.appendChild(shareToast);

                article.appendChild(title);
                article.appendChild(content);
                article.appendChild(meta);
                article.appendChild(actions);

                storedPostsContainer.appendChild(article);
            });
        }
    } catch (err) {
        console.error('Network error loading posts:', err);
    }
}

// ---------------------------------------------------------------------------
// Social Features Handlers: Likes, Sharing, and Comments
// ---------------------------------------------------------------------------

async function handleLikeToggle(form) {
    const btn = form.querySelector('.like-btn');
    if (!btn || btn.disabled) return;

    const postId = form.dataset.postId || form.action.match(/\/posts\/(\d+)\/like\/?/)?.[1];
    if (!postId) return;

    const csrfToken = getCsrfToken();
    btn.disabled = true;

    try {
        const response = await fetch(`/posts/${postId}/like/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            }
        });

        if (response.status === 401) {
            window.location.href = `/login/?next=/posts/${postId}/`;
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to toggle like.');
        }

        const data = await response.json();
        if (data.success) {
            // Update all like buttons for this post on the page (in case there are multiple)
            const postLikeForms = document.querySelectorAll(`.like-form[data-post-id="${postId}"]`);
            postLikeForms.forEach(f => {
                const b = f.querySelector('.like-btn');
                if (!b) return;
                if (data.liked) {
                    b.classList.add('liked');
                } else {
                    b.classList.remove('liked');
                }
                const icon = b.querySelector('.like-icon');
                const text = b.querySelector('.like-text');
                const count = b.querySelector('.like-count');

                if (icon) icon.textContent = data.liked ? '♥' : '♡';
                if (text) text.textContent = data.liked ? 'Liked' : 'Like';
                if (count) count.textContent = `(${data.like_count})`;
            });
        }
    } catch (err) {
        console.error('Error toggling like:', err);
    } finally {
        btn.disabled = false;
    }
}

async function handleShare(btn) {
    const url = btn.dataset.shareUrl || window.location.href;
    const title = btn.dataset.shareTitle || document.title;
    const container = btn.parentElement;
    const toast = container ? container.querySelector('.share-toast') : null;

    if (navigator.share) {
        try {
            await navigator.share({ title: title, url: url });
            return;
        } catch (err) {
            if (err.name === 'AbortError') {
                return; // User canceled
            }
            // Fall through to clipboard fallback
        }
    }

    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(url);
        } else {
            const tempInput = document.createElement('input');
            tempInput.value = url;
            document.body.appendChild(tempInput);
            tempInput.select();
            document.execCommand('copy');
            document.body.removeChild(tempInput);
        }

        if (toast) {
            toast.textContent = 'Link copied!';
            toast.style.display = 'inline-block';
            setTimeout(() => {
                toast.style.display = 'none';
            }, 2500);
        } else {
            const originalText = btn.innerHTML;
            btn.innerHTML = `<span class="share-icon">✓</span><span class="share-text">Copied!</span>`;
            setTimeout(() => {
                btn.innerHTML = originalText;
            }, 2500);
        }
    } catch (err) {
        console.error('Failed to copy share link:', err);
        prompt('Copy this permanent post URL:', url);
    }
}

async function handleCommentSubmit(form) {
    const textarea = form.querySelector('#comment-content');
    const submitBtn = form.querySelector('button[type="submit"]');
    const content = textarea ? textarea.value.trim() : '';

    if (!content) {
        alert('Please write a comment before posting.');
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Posting...';
    }

    try {
        const csrfToken = getCsrfToken();
        const action = form.action;
        const response = await fetch(action, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ content })
        });

        if (response.status === 401) {
            window.location.href = `/login/?next=${window.location.pathname}`;
            return;
        }

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            alert(data.error || 'Could not post comment.');
            return;
        }

        form.reset();

        // Update comment counter elements
        const totalCountEl = document.getElementById('total-comment-count');
        if (totalCountEl && typeof data.comment_count !== 'undefined') {
            totalCountEl.textContent = data.comment_count;
        }
        const badgeCountEl = document.querySelector('.comment-count-badge .comment-count-text');
        if (badgeCountEl && typeof data.comment_count !== 'undefined') {
            badgeCountEl.textContent = `${data.comment_count} comment${data.comment_count === 1 ? '' : 's'}`;
        }

        // Remove empty state if present
        const noCommentsMsg = document.getElementById('no-comments-msg');
        if (noCommentsMsg) {
            noCommentsMsg.remove();
        }

        // Add new comment to list
        const commentList = document.getElementById('comment-list');
        if (commentList && data.comment) {
            const comment = data.comment;
            const article = document.createElement('article');
            article.className = 'comment-card';
            article.id = `comment-${comment.id}`;

            const basePath = window.location.pathname.endsWith('/') ? window.location.pathname : window.location.pathname + '/';

            article.innerHTML = `
                <div class="comment-header">
                    <div class="comment-author-info">
                        <strong><a href="${escapeHtml(comment.author_profile_url)}">${escapeHtml(comment.author)}</a></strong>
                        <span class="comment-date">&middot; ${escapeHtml(comment.created_at)}</span>
                    </div>
                    <div class="comment-actions">
                        <a href="${basePath}comments/${comment.id}/edit/" class="action-btn-link">Edit</a>
                        <form method="post" action="${basePath}comments/${comment.id}/delete/" class="inline-form"
                            onsubmit="return confirm('Delete this comment?');">
                            <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                            <button type="submit" class="danger-btn">Delete</button>
                        </form>
                    </div>
                </div>
                <div class="comment-body">
                    <p>${escapeHtml(comment.content).replace(/\\n/g, '<br>')}</p>
                </div>
            `;
            commentList.appendChild(article);
        }
    } catch (err) {
        console.error('Error posting comment via fetch:', err);
        // Fall back to native form submission
        form.submit();
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Post Comment';
        }
    }
}

// Global delegated event listeners for dynamic and static elements
document.addEventListener('submit', (e) => {
    const likeForm = e.target.closest('.like-form');
    if (likeForm) {
        e.preventDefault();
        handleLikeToggle(likeForm);
        return;
    }

    const commentForm = e.target.closest('#comment-form');
    if (commentForm) {
        e.preventDefault();
        handleCommentSubmit(commentForm);
        return;
    }
});

document.addEventListener('click', (e) => {
    const shareBtn = e.target.closest('.share-btn');
    if (shareBtn) {
        e.preventDefault();
        handleShare(shareBtn);
    }
});

document.addEventListener('DOMContentLoaded', () => {
    checkServerPort();
    loadPosts();
});

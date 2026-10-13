function getCsrfToken() {
    const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (tokenInput && tokenInput.value) {
        return tokenInput.value;
    }
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
}

const createForm = document.getElementById('create-form');

if (createForm) {
    createForm.addEventListener('submit', handleCreatePost);
}

function checkServerPort() {
    const errorDiv = document.getElementById('form-error');
    if (window.location.port && window.location.port !== '8000') {
        if (errorDiv) {
            errorDiv.innerHTML = `⚠️ <strong>Note:</strong> You are currently viewing this page through Live Server on <strong>port ${window.location.port}</strong>.<br><br>The Django backend is running on <strong>port 8000</strong>. Please open <a href="http://127.0.0.1:8000/create.html" style="color: #0d47a1; text-decoration: underline; font-weight: bold;">http://127.0.0.1:8000/create.html</a> to publish posts to the database.`;
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
            errorDiv.innerHTML = `⚠️ <strong>Cannot Publish:</strong> You are submitting from <strong>port ${window.location.port}</strong> (Live Server), which cannot connect to Django.<br><br>👉 Please open and submit via <a href="http://127.0.0.1:8000/create.html" style="color: #0d47a1; text-decoration: underline; font-weight: bold;">http://127.0.0.1:8000/create.html</a>.`;
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

        if (!response.ok) {
            throw new Error(data.error || `Server returned error (${response.status} ${response.statusText}).`);
        }

        createForm.reset();
        localStorage.removeItem('posts');

        window.location.href = 'index.html#explore';
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

        if (storedPostsContainer) {
            storedPostsContainer.innerHTML = '';

            posts.forEach(post => {
                const article = document.createElement('article');

                const title = document.createElement('h3');
                title.textContent = post.title;

                const content = document.createElement('p');
                content.textContent = post.content;

                const meta = document.createElement('p');
                meta.style.color = '#666';
                meta.style.fontSize = '14px';

                const date = new Date(post.created_at);
                const formattedDate = !isNaN(date.getTime())
                    ? date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                    })
                    : '';

                meta.textContent = 'posted ' + formattedDate;

                article.appendChild(title);
                article.appendChild(content);
                article.appendChild(meta);

                storedPostsContainer.appendChild(article);
            });
        }
    } catch (err) {
        console.error('Network error loading posts:', err);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    checkServerPort();
    loadPosts();
});


const createForm = document.getElementById('create-form');

if (createForm) {
    createForm.addEventListener('submit', handleCreatePost);
}

function handleCreatePost(e) {
    e.preventDefault();

    const title = document.getElementById('post-title').value.trim();
    const content = document.getElementById('post-content').value.trim();
    const errorDiv = document.getElementById('form-error');

    if (!title || !content) {
        errorDiv.textContent = 'Please fill in both title and content.';
        errorDiv.style.display = 'block';
        return;
    }

    errorDiv.style.display = 'none';

    const post = {
        id: Date.now(),
        title,
        content,
        createdAt: new Date().toISOString()
    };

    const posts = JSON.parse(localStorage.getItem('posts')) || [];
    posts.unshift(post);
    localStorage.setItem('posts', JSON.stringify(posts));

    createForm.reset();

    setTimeout(() => {
        window.location.href = 'index.html#explore';
    }, 300);
}

function loadPostsFromStorage() {
    const exploreSection = document.getElementById('explore');
    if (!exploreSection) return;

    const posts = JSON.parse(localStorage.getItem('posts')) || [];
    let storedPostsContainer = document.getElementById('stored-posts-container');

    if (!storedPostsContainer && posts.length > 0) {
        storedPostsContainer = document.createElement('div');
        storedPostsContainer.id = 'stored-posts-container';
        const heading = exploreSection.querySelector('h2');
        heading.insertAdjacentElement('afterend', storedPostsContainer);
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

            const date = new Date(post.createdAt);
            const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });

            meta.textContent = 'posted ' + formattedDate;

            article.appendChild(title);
            article.appendChild(content);
            article.appendChild(meta);

            storedPostsContainer.appendChild(article);
        });
    }
}

document.addEventListener('DOMContentLoaded', loadPostsFromStorage);

from django.conf import settings
from django.db import models


class Post(models.Model):
    """
    Represents a user-created post on the platform.

    'author' is a ForeignKey to the user model (AUTH_USER_MODEL).
    - on_delete=CASCADE: if the user is deleted, their posts are deleted too.
    - related_name='posts': allows user.posts.all() to fetch a user's posts.
    - The field is required (NOT NULL). Every post must have an owner.
    """
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        author_name = self.author.username if self.author else "Unknown author"
        return f"{self.title} (by {author_name})"


class Like(models.Model):
    """
    Represents a user liking a post.
    Enforces uniqueness so a user can only like a post once at the database level.
    """
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'post'],
                name='unique_user_post_like'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} likes '{self.post.title}'"


class Comment(models.Model):
    """
    Represents a persistent comment on a post by an authenticated user.
    """
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on '{self.post.title}'"

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

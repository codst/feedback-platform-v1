from django.contrib import admin
from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    # Display author alongside title in the list view
    list_display = ('id', 'title', 'author', 'created_at')
    # Allow filtering by author and date
    list_filter = ('author', 'created_at')
    # Allow searching by title, content, or author's username
    search_fields = ('title', 'content', 'author__username')
    ordering = ('-created_at',)
    # raw_id_fields improves the author picker for large user tables
    raw_id_fields = ('author',)

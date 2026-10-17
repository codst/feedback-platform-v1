from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    """
    ModelForm for creating and editing posts.

    Key points for a Django learner:
    - ModelForm automatically generates fields from the model.
    - We only expose 'title' and 'content'. The 'author' field is NEVER
    included here — it is always set from request.user in the view.
    This makes it impossible for a user to forge authorship via the form.
    """
    class Meta:
        model = Post
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': "What's your idea?",
                'id': 'post-title',
            }),
            'content': forms.Textarea(attrs={
                'placeholder': 'Share the details...',
                'id': 'post-content',
            }),
        }
        error_messages = {
            'title': {
                'required': 'Please enter a title.',
                'max_length': 'Title must be 200 characters or fewer.',
            },
            'content': {
                'required': 'Please enter some content.',
            },
        }


class CommentForm(forms.ModelForm):
    """
    ModelForm for creating and editing comments.

    'author' and 'post' are never included in the form fields.
    They are always assigned server-side from request.user and the URL post_id.
    """
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'placeholder': 'Share constructive feedback: What works well? What could be improved? Ideas for next steps...',
                'id': 'comment-content',
                'rows': 3,
            }),
        }
        error_messages = {
            'content': {
                'required': 'Comment cannot be empty.',
                'max_length': 'Comment must be 2000 characters or fewer.',
            },
        }

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise forms.ValidationError('Comment cannot be empty.')
        if len(content) > 2000:
            raise forms.ValidationError('Comment must be 2000 characters or fewer.')
        return content

from django import forms
from .models import Post


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

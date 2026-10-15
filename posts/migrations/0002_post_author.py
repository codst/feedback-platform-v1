# Generated manually for Phase 2: adds author ForeignKey to Post.
#
# Migration strategy (approved by user):
#   - default=1 assigns the 5 existing authorless posts to user id=1 (superuser "chhayank").
#   - After this migration, the author column is NOT NULL — every new post must have an author.
#   - No posts are deleted; no data is invented.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='author',
            field=models.ForeignKey(
                # default=1 is the superuser "chhayank" who approved this migration.
                # This only affects the 5 existing rows; new posts always receive the
                # request.user from the view — never a client-supplied value.
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='posts',
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,  # Remove the default after applying; column stays NOT NULL.
        ),
    ]

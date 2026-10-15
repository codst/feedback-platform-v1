# Data migration: Assign legacy posts (IDs 2 to 6) to dedicated 'system' user

from django.db import migrations


def assign_legacy_posts_to_system_user(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Post = apps.get_model('posts', 'Post')

    # Create or get dedicated system user for legacy posts
    system_user, _ = User.objects.get_or_create(
        username='system',
        defaults={
            'email': 'system@feedbackplatform.local',
            'password': '!',  # unusable password in Django
            'is_active': False,  # Inactive system account
        }
    )

    # Legacy post IDs created before user authentication was added
    legacy_ids = [2, 3, 4, 5, 6]
    Post.objects.filter(id__in=legacy_ids).update(author=system_user)


def reverse_assignment(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0003_alter_post_options_alter_post_author'),
    ]

    operations = [
        migrations.RunPython(assign_legacy_posts_to_system_user, reverse_assignment),
    ]

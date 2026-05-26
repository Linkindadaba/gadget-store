# Generated migration to add profile_picture field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_review'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='profile_picture',
            field=models.ImageField(blank=True, null=True, upload_to='profiles/'),
        ),
    ]


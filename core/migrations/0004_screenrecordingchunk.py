# Generated by Django 5.2 on 2025-04-14 07:18

import core.models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_interview'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScreenRecordingChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_number', models.CharField(max_length=10)),
                ('recording', models.FileField(upload_to=core.models.screen_recording_path)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('interview', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screen_recording_chunks', to='core.interview')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]

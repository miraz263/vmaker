import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RenderJob',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('QUEUED', 'Queued in Task Engine'), ('AUDIO_GENERATING', 'Generating Voice Narration & Audio'), ('SCENE_COMPILING', 'Compiling 3D Scene Frames & Visuals'), ('ENCODING', 'Encoding Final MP4 Video'), ('COMPLETED', 'Video Rendering Complete'), ('FAILED', 'Rendering Failed')], default='QUEUED', max_length=30)),
                ('progress', models.PositiveSmallIntegerField(default=0, help_text='Rendering progress (0% - 100%)')),
                ('resolution', models.CharField(default='1080p', max_length=20)),
                ('fps', models.PositiveSmallIntegerField(default=24)),
                ('output_file', models.FileField(blank=True, null=True, upload_to='videos/renders/')),
                ('video_url', models.CharField(blank=True, max_length=500)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='render_jobs', to='projects.project')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]

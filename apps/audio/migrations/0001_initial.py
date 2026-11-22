import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('scenes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SceneAudio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('audio_file', models.FileField(upload_to='audio/narration/')),
                ('voice', models.CharField(default='bn-BD-NabanitaNeural', max_length=60)),
                ('duration', models.FloatField(default=0.0)),
                ('visemes', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('scene', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='audio_track', to='scenes.scene')),
            ],
        ),
    ]

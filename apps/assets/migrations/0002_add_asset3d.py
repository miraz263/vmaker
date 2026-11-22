from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Asset3D',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('category', models.CharField(choices=[('character', '3D Character Avatar'), ('environment', '3D Scene Environment'), ('prop', '3D Prop / Object')], default='character', max_length=50)),
                ('file', models.FileField(upload_to='models/3d/')),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='models/thumbnails/')),
                ('has_visemes', models.BooleanField(default=True, help_text='Supports mouth blendshapes for audio lip-sync')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Default scale, camera offset, animations list')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='AnimationClip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('clip_file', models.FileField(upload_to='models/animations/')),
                ('duration', models.FloatField(default=1.0)),
                ('loop', models.BooleanField(default=True)),
            ],
        ),
    ]

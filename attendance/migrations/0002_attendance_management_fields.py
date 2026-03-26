from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0001_initial'),
        ('courses', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='batch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attendance_records', to='batches.batch'),
        ),
        migrations.AddField(
            model_name='attendance',
            name='course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attendance_records', to='courses.course'),
        ),
        migrations.AddField(
            model_name='attendance',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='remarks',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='session_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='status',
            field=models.CharField(choices=[('PRESENT', 'Present'), ('ABSENT', 'Absent')], default='PRESENT', max_length=10),
        ),
        migrations.AddField(
            model_name='attendance',
            name='trainer',
            field=models.ForeignKey(blank=True, limit_choices_to={'role': 'TRAINER'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='marked_attendance_records', to=settings.AUTH_USER_MODEL),
        ),
    ]

from django.db import migrations


def backfill_enrollment_course(apps, schema_editor):
    Enrollment = apps.get_model('enrollments', 'Enrollment')
    for enrollment in Enrollment.objects.filter(course__isnull=True).select_related('batch'):
        if enrollment.batch_id:
            enrollment.course_id = enrollment.batch.course_id
            enrollment.save(update_fields=['course'])


class Migration(migrations.Migration):

    dependencies = [
        ('enrollments', '0002_alter_enrollment_unique_together_enrollment_course_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_enrollment_course, migrations.RunPython.noop),
    ]

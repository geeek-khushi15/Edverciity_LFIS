from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_remove_studentdoubt_category_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainerprofile',
            name='address',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='contact_number',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='department',
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='father_name',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='full_name',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='gender',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='highest_education',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='pincode',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='profile_photo',
            field=models.ImageField(blank=True, null=True, upload_to='trainer_photos/'),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='specialization',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='trainer_id',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='trainerprofile',
            name='years_of_experience',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]

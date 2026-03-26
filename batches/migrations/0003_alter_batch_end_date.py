from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('batches', '0002_batch_module'),
    ]

    operations = [
        migrations.AlterField(
            model_name='batch',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BBulkSmash', '0003_appsettings_pre_run_delay'),
    ]

    operations = [
        migrations.AddField(
            model_name='appsettings',
            name='trace_err',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='uacappconfig',
            name='auto_accept_options',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='uasappconfig',
            name='auto_accept_options',
            field=models.BooleanField(default=False),
        ),
    ]

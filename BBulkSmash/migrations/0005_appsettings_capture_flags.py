from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BBulkSmash', '0004_appsettings_trace_err_auto_accept_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='appsettings',
            name='capture_sip',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='appsettings',
            name='capture_sip_rtp',
            field=models.BooleanField(default=False),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BBulkSmash', '0002_appsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='appsettings',
            name='pre_run_delay',
            field=models.PositiveIntegerField(default=0,
                help_text='Seconds to wait after launching SIPp before it starts sending calls (0 = no delay)'),
        ),
    ]

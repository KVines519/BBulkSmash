from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BBulkSmash', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trace_stat',      models.BooleanField(default=False)),
                ('trace_msg',       models.BooleanField(default=False)),
                ('trace_counts',    models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'App Settings',
            },
        ),
    ]

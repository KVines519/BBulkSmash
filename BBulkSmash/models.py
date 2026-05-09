from django.db import models


class AppSettings(models.Model):
    """Singleton model for global app settings (trace flags, etc.)."""
    trace_stat   = models.BooleanField(default=False)
    trace_msg    = models.BooleanField(default=False)
    trace_counts = models.BooleanField(default=False)
    trace_err    = models.BooleanField(default=False)
    pre_run_delay = models.PositiveIntegerField(default=0,
        help_text='Seconds to wait after launching SIPp before it starts sending calls (0 = no delay)')
    capture_sip = models.BooleanField(default=False)
    capture_sip_rtp = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'App Settings'

    def __str__(self):
        return 'App Settings'

    @classmethod
    def get(cls):
        """Always return the single settings row, creating it if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class UacAppConfig(models.Model):
    uac_key = models.CharField(max_length=8, unique=True, default='uac_1')
    uac_config_name = models.CharField(max_length=28, unique=True, default='Default UAC') 
    select_uac = models.CharField(max_length=100, default='uac_basic.xml')
    uac_remote = models.GenericIPAddressField(default='10.0.0.10')
    uac_remote_port = models.PositiveIntegerField(default=5060)
    uac_local = models.GenericIPAddressField(default='10.0.0.5')
    uac_local_port = models.PositiveIntegerField(default=5060)
    uac_protocol = models.CharField(max_length=10, choices=[('un', 'UDP'), ('tn', 'TCP')], default='un')
    total_no_of_calls = models.PositiveIntegerField(default=1)
    cps = models.PositiveIntegerField(default=1)
    max_ccl = models.PositiveIntegerField(default=1)

    # More options form fields
    called_party = models.CharField(max_length=50, blank=True)
    calling_party = models.CharField(max_length=50, blank=True)
    min_rtp_port = models.PositiveIntegerField(default=10000)
    max_rtp_port = models.PositiveIntegerField(default=20000)
    csv_inf = models.CharField(max_length=100, blank=True, null=True)
    stun_server = models.CharField(max_length=255, null=True, blank=True)
    auto_accept_options = models.BooleanField(default=False)

    is_active_config = models.BooleanField(default=False)

    def __str__(self):
        return self.uac_config_name
    
    def save(self, *args, **kwargs):
        # If this config is being set as active, ensure all others are set to False
        if self.is_active_config:
            UacAppConfig.objects.exclude(pk=self.pk).update(is_active_config=False)
        super().save(*args, **kwargs)



class UasAppConfig(models.Model):
    uas_key = models.CharField(max_length=8, unique=True, default='uas_1')
    uas_config_name = models.CharField(max_length=28, unique=True, default='Default UAS') 
    select_uas = models.CharField(max_length=100, default='uas_basic.xml')
    uas_remote = models.GenericIPAddressField(default='10.0.0.20')
    uas_remote_port = models.PositiveIntegerField(default=5060)
    uas_local = models.GenericIPAddressField(default='10.0.0.5')
    uas_local_port = models.PositiveIntegerField(default=5060)
    uas_protocol = models.CharField(max_length=10, choices=[('un', 'UDP'), ('tn', 'TCP')], default='un')
    cps = models.PositiveIntegerField(default=1)
    max_ccl = models.PositiveIntegerField(default=1)

    # More options form fields
    min_rtp_port = models.PositiveIntegerField(default=10000)
    max_rtp_port = models.PositiveIntegerField(default=20000)
    csv_inf = models.CharField(max_length=100, blank=True, null=True)
    auto_accept_options = models.BooleanField(default=False)

    is_active_config = models.BooleanField(default=False)

    def __str__(self):
        return self.uas_config_name

    def save(self, *args, **kwargs):
        # If this config is being set as active, ensure all others are set to False
        if self.is_active_config:
            UasAppConfig.objects.exclude(pk=self.pk).update(is_active_config=False)
        super().save(*args, **kwargs)

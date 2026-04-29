from django import forms
from django.conf import settings
import os
from pathlib import Path
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import UacAppConfig, UasAppConfig

import logging
logger = logging.getLogger(__name__)

class UACForm(forms.ModelForm):
    # UAC Config Fields
    uac_key = forms.ChoiceField(
        label='Select Config',
        choices=[],  #this is set in __init__
        required=True
    )
    uac_config_name = forms.CharField(
        label='Config Name',
        required=True,
        max_length=28
    )
    uac_remote = forms.GenericIPAddressField(label='UAC Remote Address', protocol='IPv4')
    uac_remote_port = forms.IntegerField(label='UAC Remote Port', min_value=1024, max_value=65535, initial=5060)
    uac_local = forms.GenericIPAddressField(label='UAC Local Address', protocol='IPv4')
    uac_local_port = forms.IntegerField(label='UAC Local Port', min_value=1024, max_value=65535, initial=5060)
    uac_protocol = forms.ChoiceField(label='UAC Protocol', choices=[('un', 'UDP'), ('tn', 'TCP')])

    # UAC XML Selection
    select_uac = forms.ChoiceField(label='Select UAC XML Scenario')

    # SIPp Options
    called_party = forms.CharField(
        label='Called Party',
        max_length=50,
        required=False,
        validators=[RegexValidator(regex=r'^(\+[0-9]+|[a-zA-Z0-9]+)$', message='Enter a valid phone number or alphanumeric ID.')]
    )
    calling_party = forms.CharField(
        label='Calling Party',
        max_length=50,
        required=False,
        validators=[RegexValidator(regex=r'^(\+[0-9]+|[a-zA-Z0-9]+)$', message='Enter a valid phone number or alphanumeric ID.')]
    )
    total_no_of_calls = forms.IntegerField(
        label='No. of calls to send',
        min_value=1,
        max_value=28000,
        required=True,
        initial=1
    )
    cps = forms.IntegerField(
        label='Calls Per Second',
        min_value=1,
        max_value=200,
        required=True,
        initial=1
    )
    max_ccl = forms.IntegerField(
        label='Max Concurrent Calls',
        min_value=1,
        max_value=5000,
        required=True,
        initial=1
    )
    min_rtp_port = forms.IntegerField(
        label='Min RTP Port',
        min_value=1024,
        max_value=65535,
        required=True,
        initial=10000
    )
    max_rtp_port = forms.IntegerField(
        label='Max RTP Port',
        min_value=1024,
        max_value=65535,
        required=True,
        initial=20000
    )
    csv_inf = forms.ChoiceField(
        label='CSV Injection File',
        choices=[],  #set in __init__
        required=False 
    )

    stun_server = forms.GenericIPAddressField(
        label='STUN Server',
        protocol='IPv4',
        required=False,
        initial='162.159.207.0'
    )

    class Meta:
        model = UacAppConfig
        fields = [
            # 'uac_key', #manually defined field
            'uac_config_name',
            'uac_remote', 'uac_remote_port',
            'uac_local', 'uac_local_port', 'uac_protocol',
            'select_uac',
            'called_party', 'calling_party',
            'total_no_of_calls', 'cps', 'max_ccl', 'csv_inf', 'stun_server',
            'min_rtp_port', 'max_rtp_port',
        ]

    def __init__(self, *args, uac_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['select_uac'].choices = self._get_xml_file_choices('uac')
        if uac_choices:
            self.fields['uac_key'].choices = uac_choices
            self.fields['uac_key'].initial = self.instance.uac_key

        self.fields['csv_inf'].choices = self._get_csv_file_choices()
        self.fields['csv_inf'].initial = self.instance.csv_inf or ''


    def _get_xml_file_choices(self, prefix):
        xml_dir = Path(settings.BASE_DIR) / 'BBulkSmash' / 'xml'
        try:
            return sorted([
                (f, f) for f in os.listdir(xml_dir)
                if f.endswith('.xml') and f.startswith(prefix)
            ])
        except FileNotFoundError:
            return []
        
    def _get_csv_file_choices(self):
        csv_dir = Path(settings.BASE_DIR) / 'BBulkSmash' / 'xml' / 'csv'
        try:
            csv_files = sorted([
                (f, f) for f in os.listdir(csv_dir)
                if f.endswith('.csv')
            ])
            if not csv_files:
                return [('', 'No CSV File Found')]
            return [('', 'No CSV Selected')] + csv_files
        except FileNotFoundError:
            return [('', 'No CSV File Found')]



class UASForm(forms.ModelForm):
    # UAS Config Fields
    uas_key = forms.ChoiceField(
        label='Select Config',
        choices=[],  #this is set in __init__
        required=True
    )
    uas_config_name = forms.CharField(
        label='Config Name',
        required=True,
        max_length=28
    )
    uas_remote = forms.GenericIPAddressField(label='UAS Remote Address', protocol='IPv4')
    uas_remote_port = forms.IntegerField(label='UAS Remote Port', min_value=1024, max_value=65535, initial=5060)
    uas_local = forms.GenericIPAddressField(label='UAS Local Address', protocol='IPv4')  # Optional if shared
    uas_local_port = forms.IntegerField(label='UAS Local Port', min_value=1024, max_value=65535, initial=5060)
    uas_protocol = forms.ChoiceField(label='UAS Protocol', choices=[('un', 'UDP'), ('tn', 'TCP')])

    # UAS XML Selection
    select_uas = forms.ChoiceField(label='Select UAS XML Scenario')

    # SIPp Options
    cps = forms.IntegerField(
        label='Calls Per Second',
        min_value=1,
        max_value=200,
        required=True,
        initial=1
    )
    max_ccl = forms.IntegerField(
        label='Max Concurrent Calls',
        min_value=1,
        max_value=5000,
        required=True,
        initial=1
    )
    min_rtp_port = forms.IntegerField(
        label='Min RTP Port',
        min_value=1024,
        max_value=65535,
        required=True,
        initial=10000
    )
    max_rtp_port = forms.IntegerField(
        label='Max RTP Port',
        min_value=1024,
        max_value=65535,
        required=True,
        initial=20000
    )
    csv_inf = forms.ChoiceField(
        label='CSV Injection File',
        choices=[],  #set in __init__
        required=False 
    )

    class Meta:
        model = UasAppConfig
        fields = [
            # 'uas_key',
            'uas_config_name',
            'uas_remote', 'uas_remote_port',
            'uas_local', 'uas_local_port',
            'uas_protocol', 'select_uas',
            'cps', 'max_ccl', 'csv_inf',
            'min_rtp_port', 'max_rtp_port',
        ]

    def __init__(self, *args, uas_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['select_uas'].choices = self._get_xml_file_choices('uas')
        if uas_choices:
            self.fields['uas_key'].choices = uas_choices
            self.fields['uas_key'].initial = self.instance.uas_key

        self.fields['csv_inf'].choices = self._get_csv_file_choices()
        self.fields['csv_inf'].initial = self.instance.csv_inf or ''

    def _get_xml_file_choices(self, prefix):
        xml_dir = Path(settings.BASE_DIR) / 'BBulkSmash' / 'xml'
        try:
            return sorted([
                (f, f) for f in os.listdir(xml_dir)
                if f.endswith('.xml') and f.startswith(prefix)
            ])
        except FileNotFoundError:
            return []
        
    def _get_csv_file_choices(self):
        csv_dir = Path(settings.BASE_DIR) / 'BBulkSmash' / 'xml' / 'csv'
        try:
            csv_files = sorted([
                (f, f) for f in os.listdir(csv_dir)
                if f.endswith('.csv')
            ])
            if not csv_files:
                return [('', 'No CSV File Found')]
            return [('', 'No CSV Selected')] + csv_files
        except FileNotFoundError:
            return [('', 'No CSV File Found')]

class xpcUploadForm(forms.Form):
    file = forms.FileField(label='Select an XML, PCAP, CSV, or WAV file', help_text='XML file name should start with "uac" or "uas".',
                           widget=forms.ClearableFileInput(attrs={'accept': '.xml, .pcap, .csv, .wav', 'max_upload_size': 1048576}))

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        if not uploaded_file.name.lower().endswith('.pcap') and not uploaded_file.name.lower().endswith('.xml') and not uploaded_file.name.lower().endswith('.csv') and not uploaded_file.name.lower().endswith('.wav'):
            raise ValidationError('Only .xml, .pcap, .csv, and .wav files are allowed.')

        if uploaded_file.name.lower().endswith('.xml') and not uploaded_file.name.lower().startswith(('uac', 'uas')):
            raise ValidationError('File name should start with "uac" or "uas" and have .xml extension.')
        
        max_upload_size = 1048576  # 1 MB in bytes
        if uploaded_file.size > max_upload_size:
            raise ValidationError('File size exceeds the maximum allowed limit (1 MB).')
        
        filename = uploaded_file.name.lower()
        if len(filename) > 80:
            raise ValidationError('File name is too long. Maximum 80 characters allowed. Rename the file and try again.')

        return uploaded_file

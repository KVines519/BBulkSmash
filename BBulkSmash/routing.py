from django.urls import re_path
from . import consumers

# URL patterns use string concatenation to avoid tool corruption of regex $ anchors
_sipp_logs_pattern = r'ws/sipp_logs/' + r'$'
_sngrep_pattern = r'ws/sngrep/' + r'$'

websocket_urlpatterns = [
    re_path(_sipp_logs_pattern, consumers.SippLogConsumer.as_asgi()),
    re_path(_sngrep_pattern, consumers.SngrepConsumer.as_asgi()),
]

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
import BBulkSmash.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BBulkSmash_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(
        BBulkSmash.routing.websocket_urlpatterns
    ),
})

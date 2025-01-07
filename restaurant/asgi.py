import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from inventory import routing as inventory_routing
from pos import routing as pos_routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            inventory_routing.websocket_urlpatterns + pos_routing.websocket_urlpatterns
        )
    ),
})

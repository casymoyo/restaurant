from django.urls import re_path
from pos.consumers import SalesConsumer

websocket_urlpatterns = [
    re_path(r'^ws/sales/$', SalesConsumer.as_asgi()),
]

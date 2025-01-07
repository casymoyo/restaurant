from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/chat/<int:entry_id>/', consumers.ChatConsumer.as_asgi()),
]

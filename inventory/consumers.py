import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Notification
from loguru import logger

class NotificationConsumer(AsyncWebsocketConsumer):
    pass
    # async def connect(self):
    #     self.user = self.scope["user"]
    #     if self.user.is_authenticated:
    #         logger.info('here')
    #         self.group_name = f'user_{self.user.id}'

    #         await self.channel_layer.group_add(
    #             self.group_name,
    #             self.channel_name
    #         )
    #         await self.accept()

    # async def disconnect(self, close_code):
    #     await self.channel_layer.group_discard(
    #         self.group_name,
    #         self.channel_name
    #     )

    # async def send_notification(self, event):
    #     message = event['message']

    #     await self.send(text_data=json.dumps({
    #         'message': message
    #     }))

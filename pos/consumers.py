# import json
# from channels.generic.websocket import AsyncWebsocketConsumer

# class SalesConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         await self.channel_layer.group_add("sales_group", self.channel_name)
#         await self.accept()

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard("sales_group", self.channel_name)

#     async def send_sales_update(self, event):
#         await self.send(text_data=json.dumps(event['data']))

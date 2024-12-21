import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SalesConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        self.group_name = "sales_group"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.channel_layer.group_send(
            self.group_name,
            {

                "type": "send_sales_update",
                "data": data,
            }
        )

    async def send_sales_update(self, event):
        data = event["data"]
        print(data, 'websocket data')

        await self.send(text_data=json.dumps({
            "type": "sales_update",
            "data": data
        }))

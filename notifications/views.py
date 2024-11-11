from django.shortcuts import render
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def test(request):
    # Send a notification message to the WebSocket group
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "notifications",
        {
            'type': 'send_notification',
            'message': 'This is a test notification from the test view!'
        }
    )
    
    return render(request, 'test.html')
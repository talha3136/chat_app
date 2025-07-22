import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import ChatRoom, Message, User
from .serializers import MessageSerializer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Authenticate user
        user = self.scope["user"]
        if user == AnonymousUser():
            await self.close()
            return
        
        # Set user online
        await self.set_user_online(user, True)
        
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Set user offline
        user = self.scope["user"]
        if user != AnonymousUser():
            await self.set_user_online(user, False)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'chat_message':
            content = text_data_json['content']
            sender_id = text_data_json['sender_id']
            room_id = text_data_json['room_id']
            
            # Save message to database
            message = await self.save_message(room_id, sender_id, content)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': MessageSerializer(message).data
                }
            )
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'notification',
                    'message': f"New message from {message.sender.username}: {message.content}",
                    'sender_id': sender_id,
                    'room_id': room_id
                }
            )

        elif message_type == 'typing':
            user = self.scope["user"]
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': user.id,
                    'username': user.username,
                    'is_typing': text_data_json['is_typing']
                }
            )

    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }))

    async def typing_indicator(self, event):
        user = self.scope["user"]

        # Don't send typing indicator to the one who is typing
        if user.id != event['user_id']:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))


    async def notification(self, event):
        user = self.scope["user"]

        # Don't send notification to the sender
        if user.id != event.get('sender_id'):
            await self.send(text_data=json.dumps({
                'type': 'notification',
                'message': event['message'],
                'room_id': event['room_id']
            }))

    @database_sync_to_async
    def save_message(self, room_id, sender_id, content):
        room = ChatRoom.objects.get(id=room_id)
        sender = User.objects.get(id=sender_id)
        message = Message.objects.create(
            room=room,
            sender=sender,
            content=content
        )
        return message

    @database_sync_to_async
    def set_user_online(self, user, status):
        user.online = status
        user.save()

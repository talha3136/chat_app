from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework import viewsets, status
from .models import User, ChatRoom, Message
from .serializers import UserSerializer, ChatRoomSerializer, MessageSerializer
from django.db import models

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('chat_room')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password != password2:
            return render(request, 'register.html', {'error': 'Passwords do not match'})
        
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists'})
        
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('chat_room')
    
    return render(request, 'register.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def chat_room_view(request):
    chat_rooms = ChatRoom.objects.filter(participants=request.user)
    online_users = User.objects.filter(online=True).exclude(id=request.user.id)
    print('chat_rooms',chat_rooms)
    print('users',online_users)
    return render(request, 'chat_room.html', {
        'chat_rooms': chat_rooms,
        'online_users': online_users,
    })

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def online(self, request):
        users = User.objects.filter(online=True).exclude(id=request.user.id)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer
    
    def get_queryset(self):
        user = self.request.user
        return ChatRoom.objects.filter(participants=user)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        room = self.get_object()
        messages = room.messages.all().order_by('timestamp')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def start_chat(self, request):
        user_ids = request.data.get('user_ids', [])
        user_ids.append(request.user.id)
        
        # Get existing chat room with exactly these participants
        rooms = ChatRoom.objects.annotate(
            num_participants=models.Count('participants')
        ).filter(num_participants=len(user_ids))
        
        for room in rooms:
            if set(room.participants.values_list('id', flat=True)) == set(user_ids):
                serializer = self.get_serializer(room)
                return Response(serializer.data)
        
        # Create new chat room
        room = ChatRoom.objects.create(name=f"Chat_{len(user_ids)}")
        users = User.objects.filter(id__in=user_ids)
        room.participants.set(users)
        serializer = self.get_serializer(room)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        message.read = True
        message.save()
        return Response({'status': 'message read'})

from django.contrib import admin
from django.urls import path, include
from chat import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'chatrooms', views.ChatRoomViewSet)
router.register(r'messages', views.MessageViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.chat_room_view, name='chat_room'),
    path('api/', include(router.urls)),
]

from django.urls import path

from .views import HeartbeatView, MonitorDetailView, MonitorListView, PauseView

urlpatterns = [
    path('monitors', MonitorListView.as_view(), name='monitor-list'),
    path('monitors/<str:device_id>/heartbeat', HeartbeatView.as_view(), name='monitor-heartbeat'),
    path('monitors/<str:device_id>/pause', PauseView.as_view(), name='monitor-pause'),
    path('monitors/<str:device_id>', MonitorDetailView.as_view(), name='monitor-detail'),
]
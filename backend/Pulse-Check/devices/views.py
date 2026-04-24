from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Monitor
from .serializers import MonitorCreateSerializer
from .services import MonitorService


class MonitorListView(APIView):

    def post(self, request):
        serializer = MonitorCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        try:
            monitor = MonitorService.create(
                device_id=data['id'],
                timeout=data['timeout'],
                alert_email=data['alert_email'],
            )
        except IntegrityError:
            existing = Monitor.objects.get(device_id=data['id'])
            if existing.status == Monitor.Status.DOWN:
                monitor = MonitorService.revive(data['id'])
                return Response(
                    {
                        'message': f"Monitor '{data['id']}' is already registered. It was down — monitoring has been resumed.",
                        'current_status': monitor.status,
                        'last_heartbeat': monitor.last_heartbeat,
                    },
                    status=200,
                )
            return Response(
                {
                    'message': f"Monitor '{data['id']}' is already registered and is currently {existing.status}.",
                    'current_status': existing.status,
                    'last_heartbeat': existing.last_heartbeat,
                },
                status=200,
            )

        return Response(
            {'message': f"Monitor '{monitor.device_id}' registered. Timer started for {monitor.timeout}s."},
            status=201,
        )


class MonitorDetailView(APIView):

    def delete(self, request, device_id):
        try:
            MonitorService.delete(device_id)
        except Monitor.DoesNotExist:
            return Response({'error': f"Monitor '{device_id}' not found."}, status=404)
        return Response({'message': f"Monitor '{device_id}' deregistered successfully."}, status=200)


class HeartbeatView(APIView):

    def post(self, request, device_id):
        try:
            monitor, was_down = MonitorService.heartbeat(device_id)
        except Monitor.DoesNotExist:
            return Response({'error': f"Monitor '{device_id}' not found."}, status=404)

        if was_down:
            return Response(
                {'message': f"Device '{device_id}' is back online. Timer reset to {monitor.timeout}s."},
                status=200,
            )

        return Response({'message': f"Heartbeat received. Timer reset to {monitor.timeout}s."}, status=200)


class PauseView(APIView):

    def post(self, request, device_id):
        try:
            monitor = MonitorService.pause(device_id)
        except Monitor.DoesNotExist:
            return Response({'error': f"Monitor '{device_id}' not found."}, status=404)
        return Response({'message': f"Monitor '{monitor.device_id}' paused. No alerts will fire."}, status=200)
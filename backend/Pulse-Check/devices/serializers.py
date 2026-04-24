from rest_framework import serializers


class MonitorCreateSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=255)
    timeout = serializers.IntegerField(min_value=1)
    alert_email = serializers.EmailField()


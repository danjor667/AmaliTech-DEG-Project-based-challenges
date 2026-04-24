from rest_framework import serializers

from .models import Transaction


class PaymentRequestSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)
    currency = serializers.CharField(max_length=10)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['transaction_id', 'status', 'response', 'created_at', 'updated_at']
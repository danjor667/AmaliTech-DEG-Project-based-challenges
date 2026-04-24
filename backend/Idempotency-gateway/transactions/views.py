import uuid

from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import PaymentRequestSerializer
from .services import TransactionService


def _is_valid_uuid4(value: str) -> bool:
    try:
        val = uuid.UUID(value, version=4)
        return str(val) == value.lower()
    except ValueError:
        return False


class TransactionView(APIView):
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        idempotency_key = request.headers.get('Idempotency-Key')

        if not idempotency_key:
            return Response(
                {'error': 'Idempotency-Key header is required.'},
                status=400,
            )

        if not _is_valid_uuid4(idempotency_key):
            return Response(
                {'error': 'Idempotency-Key must be a valid UUID v4.'},
                status=400,
            )

        serializer = PaymentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        service = TransactionService()
        result = service.process_transaction(idempotency_key, serializer.validated_data)

        if 'error' in result:
            return Response({'error': result['error']}, status=result['status_code'])

        response = Response(result['data'], status=result['status_code'])
        if result['cache_hit']:
            response['X-Cache-Hit'] = 'true'

        return response
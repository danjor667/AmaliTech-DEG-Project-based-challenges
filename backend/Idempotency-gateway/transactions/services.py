import hashlib
import json
import threading
import time

from .models import Transaction

# Per-key locks so concurrent requests with the same key block until the first finishes.
_key_locks: dict[str, threading.Lock] = {}
_registry_lock = threading.Lock()


def _get_key_lock(idempotency_key: str) -> threading.Lock:
    with _registry_lock:
        if idempotency_key not in _key_locks:
            _key_locks[idempotency_key] = threading.Lock()
        return _key_locks[idempotency_key]


def _hash_body(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


class TransactionService:

    def process_transaction(self, idempotency_key: str, request_data: dict) -> dict:
        request_hash = _hash_body(request_data)
        key_lock = _get_key_lock(idempotency_key)

        with key_lock:
            try:
                txn = Transaction.objects.get(transaction_id=idempotency_key)

                if txn.request_hash != request_hash:
                    return {
                        'error': 'Idempotency key already used for a different request body.',
                        'status_code': 422,
                        'cache_hit': False,
                    }

                # Same key, same body — return the cached response.
                return {
                    'data': txn.response,
                    'status_code': txn.response.get('status_code', 200),
                    'cache_hit': True,
                }

            except Transaction.DoesNotExist:
                return self._create_and_process(idempotency_key, request_hash, request_data)

    @staticmethod
    def _create_and_process(idempotency_key: str, request_hash: str, request_data: dict) -> dict:
        txn = Transaction.objects.create(
            transaction_id=idempotency_key,
            request_hash=request_hash,
            status=Transaction.Status.PENDING,
        )

        # Simulate payment processing.
        time.sleep(2)

        amount = request_data.get('amount')
        currency = request_data.get('currency', 'GHS')

        response_data = {
            'message': f'Charged {amount} {currency}',
            'transaction_id': idempotency_key,
            'status': 'SUCCESS',
            'status_code': 201,
        }

        txn.status = Transaction.Status.COMPLETED
        txn.response = response_data
        txn.save(update_fields=['status', 'response', 'updated_at'])

        return {
            'data': response_data,
            'status_code': 201,
            'cache_hit': False,
        }
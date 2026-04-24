from django.db import models


class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING'
        COMPLETED = 'COMPLETED'

    transaction_id = models.CharField(max_length=255, unique=True)
    request_hash = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
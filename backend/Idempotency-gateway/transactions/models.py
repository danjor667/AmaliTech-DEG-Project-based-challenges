from django.db import models

# Create your models here.

class Transaction(models.Model):
    transaction_id = models.CharField(max_length=255)
    request_hash = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id'])
        ]


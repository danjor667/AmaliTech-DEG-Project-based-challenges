from django.db import models
from django.utils import timezone


class Monitor(models.Model):
    class Status(models.TextChoices):
        UP = 'up'
        DOWN = 'down'
        PAUSED = 'paused'

    device_id = models.CharField(max_length=255, unique=True)
    timeout = models.PositiveIntegerField()
    alert_email = models.EmailField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UP)
    last_heartbeat = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'monitors'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.device_id} ({self.status})'
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from django.utils import timezone as django_timezone

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # seconds

_poller_started = False


def _fire_alert(device_id: str):
    timestamp = datetime.now(timezone.utc).isoformat()
    message = f'{{"ALERT": "Device {device_id} is down!", "time": "{timestamp}"}}'
    print(message, flush=True)
    logger.critical(message)


def _poll_loop():
    from .models import Monitor

    while True:
        time.sleep(POLL_INTERVAL)
        try:
            now = django_timezone.now()
            for monitor in Monitor.objects.filter(status=Monitor.Status.UP):
                deadline = monitor.last_heartbeat + timedelta(seconds=monitor.timeout)
                if now >= deadline:
                    monitor.status = Monitor.Status.DOWN
                    monitor.save(update_fields=['status'])
                    _fire_alert(monitor.device_id)
        except Exception as e:
            logger.error('Poller error: %s', e)


def start_poller():
    global _poller_started
    if _poller_started:
        return
    _poller_started = True
    thread = threading.Thread(target=_poll_loop, daemon=True)
    thread.start()


class MonitorService:

    @staticmethod
    def create(device_id: str, timeout: int, alert_email: str):
        from .models import Monitor
        return Monitor.objects.create(
            device_id=device_id,
            timeout=timeout,
            alert_email=alert_email,
            status=Monitor.Status.UP,
        )

    @staticmethod
    def heartbeat(device_id: str):
        from .models import Monitor
        monitor = Monitor.objects.get(device_id=device_id)
        was_down = monitor.status == Monitor.Status.DOWN
        monitor.status = Monitor.Status.UP
        monitor.last_heartbeat = django_timezone.now()
        monitor.save(update_fields=['status', 'last_heartbeat'])
        return monitor, was_down

    @staticmethod
    def pause(device_id: str):
        from .models import Monitor
        monitor = Monitor.objects.get(device_id=device_id)
        monitor.status = Monitor.Status.PAUSED
        monitor.save(update_fields=['status'])
        return monitor

    @staticmethod
    def revive(device_id: str):
        from .models import Monitor
        monitor = Monitor.objects.get(device_id=device_id)
        monitor.status = Monitor.Status.UP
        monitor.last_heartbeat = django_timezone.now()
        monitor.save(update_fields=['status', 'last_heartbeat'])
        return monitor

    @staticmethod
    def delete(device_id: str):
        from .models import Monitor
        monitor = Monitor.objects.get(device_id=device_id)
        monitor.delete()
# Pulse-Check API (Watchdog Sentinel)

A Dead Man's Switch backend service that monitors remote devices and automatically fires alerts when they stop sending heartbeats. Built for **CritMon Servers Inc.** to monitor solar farms and unmanned weather stations.

---

## Architecture Diagram

![Pulse-Check Flowchart](./flowchart%20pulse.png)

---

## Setup Instructions

### Option 1 — Docker (Recommended)

**Requirements:** Docker

```bash
# 1. Clone the repository and navigate to the project
cd backend/Pulse-Check

# 2. Build and start the container
docker compose up --build
```

The API will be available at `http://localhost:8000`.

---

### Option 2 — Local (Python)

**Requirements:** Python 3.11+

```bash
# 1. Clone the repository and navigate to the project
cd backend/Pulse-Check

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# 5. Start the server
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000`.

---

## API Documentation

### `POST /monitors` — Register a Monitor

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | Unique device identifier |
| `timeout` | integer | Yes | Countdown duration in seconds |
| `alert_email` | string | Yes | Email to notify on alert |

```bash
curl -X POST http://127.0.0.1:8000/monitors \
  -H "Content-Type: application/json" \
  -d '{"id": "device-123", "timeout": 60, "alert_email": "admin@critmon.com"}'
```

**Response — `201 Created` (new device)**
```json
{
  "message": "Monitor 'device-123' registered. Timer started for 60s."
}
```

**Response — `200 OK` (already registered, currently up)**
```json
{
  "message": "Monitor 'device-123' is already registered and is currently up.",
  "current_status": "up",
  "last_heartbeat": "2026-04-24T10:00:00Z"
}
```

**Response — `200 OK` (already registered, was down — auto-revived)**
```json
{
  "message": "Monitor 'device-123' is already registered. It was down — monitoring has been resumed.",
  "current_status": "up",
  "last_heartbeat": "2026-04-24T10:00:00Z"
}
```

---

### `POST /monitors/{id}/heartbeat` — Reset the Timer

```bash
curl -X POST http://127.0.0.1:8000/monitors/device-123/heartbeat
```

**Response — `200 OK`**
```json
{ "message": "Heartbeat received. Timer reset to 60s." }
```

**Response — `200 OK` (device was previously down)**
```json
{ "message": "Device 'device-123' is back online. Timer reset to 60s." }
```

**Response — `404 Not Found`**
```json
{ "error": "Monitor 'device-123' not found." }
```

---

### `POST /monitors/{id}/pause` — Pause Monitoring

Stops the countdown. No alerts will fire while paused. Sending a heartbeat automatically un-pauses.

```bash
curl -X POST http://127.0.0.1:8000/monitors/device-123/pause
```

**Response — `200 OK`**
```json
{ "message": "Monitor 'device-123' paused. No alerts will fire." }
```

---

### `DELETE /monitors/{id}` — Deregister a Monitor

```bash
curl -X DELETE http://127.0.0.1:8000/monitors/device-123
```

**Response — `200 OK`**
```json
{ "message": "Monitor 'device-123' deregistered successfully." }
```

---

### Error Responses

| Scenario | Status | Message |
|---|---|---|
| Invalid or missing fields | `400` | Field-level validation errors |
| Monitor not found | `404` | `Monitor 'X' not found.` |

---

### Alert Output

When a monitor's timer expires the system logs the following to the console:

```json
{"ALERT": "Device device-123 is down!", "time": "2026-04-24T10:01:00Z"}
```

The monitor's status is also updated to `down` in the database.

---

## Design Decisions

### Database Polling (Dead Man's Switch Timer)
I initially implemented the countdown timer using Python's `threading.Timer`  one timer object per registered device. While this approach felt intuitive, I identified several problems that made me reconsider:

- **Lost on restart:** All timers lived in memory. A server crash or restart would silently wipe every active timer, devices would go offline and no alert would ever fire.
- **Memory pressure:** Every registered device held a live sleeping thread. With hundreds or thousands of devices this becomes a resource problem.
- **No visibility:** There was no way to inspect or debug the state of active timers without adding extra tooling.
- **Cancellation race condition:** Between cancelling the old timer and starting a new one on heartbeat, there was a brief window where no timer was active a missed alert could slip through under load.

I switched to a **single background polling thread** that wakes up every 5 seconds and queries the database for expired monitors (`now >= last_heartbeat + timeout`). All state lives in the database, not in memory.

**Trade-off of the current approach:** Alerts fire within 5 seconds of the actual timeout rather than at the exact millisecond. For a system monitoring devices that are expected to ping every 60 seconds or more, a 5-second margin is entirely acceptable and does not affect the reliability of the alert. The simplicity, persistence, and debuggability gained far outweigh this minor imprecision.

### PENDING / UP / DOWN / PAUSED Status
Explicit status tracking makes the system easy to reason about. The poller only acts on `up` monitors, ignoring `paused` and `down` ones. Status changes are always persisted before any alert fires.

### SQLite
Zero-configuration database suitable for this challenge. The Django ORM abstracts the database layer so swapping to PostgreSQL for production requires only a settings change.

---

## Developer's Choice Features

### 1. Smart Re-registration
If a client registers a device that already exists, the API responds intelligently instead of returning a generic error:
- **Status `up` or `paused`** — Returns `200` confirming the device is already registered with its current status and last heartbeat time.
- **Status `down`** — Automatically revives the monitor (resets `last_heartbeat`, sets `status = up`) and informs the client that monitoring has been resumed. This prevents the need to delete and re-register a device after an outage.

### 2. Monitor Deregistration (`DELETE /monitors/{id}`)
Permanently removes a monitor from the database. Without this, decommissioned devices would remain in the system indefinitely the poller would keep checking them and potentially fire false alerts if the record somehow ended up back in `up` state. Deregistration cleanly closes the lifecycle of a device.
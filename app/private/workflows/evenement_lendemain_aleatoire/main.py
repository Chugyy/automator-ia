from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import random
import re
import webbrowser
import time

try:
    # Tools injected by the engine/registry
    from app.private.tools.calendar.main import CalendarTool
    from app.private.tools.date.main import DateTool
    from config.config import settings
except Exception:
    # Fallback for direct execution
    from tools.calendar.main import CalendarTool
    from tools.date.main import DateTool
    class settings:  # simple fallback
        host = 'localhost'
        port = 8000


SUFFIX_PATTERN = re.compile(r"^(.*?)(?:\s-\s\d{6})$")


def _base_name(summary: str) -> str:
    if not summary:
        return summary
    m = SUFFIX_PATTERN.match(summary)
    return m.group(1) if m else summary


def _with_random_suffix(summary: str) -> str:
    base = _base_name(summary)
    digits = f"{random.randint(0, 999999):06d}"
    return f"{base} - {digits}"


def _parse_event_dt(dt_obj: Dict[str, Any]) -> datetime:
    # Handles both dateTime and date (all day)
    if not dt_obj:
        return None
    if 'dateTime' in dt_obj and dt_obj['dateTime']:
        # Normalize Z to +00:00 for fromisoformat
        dt_str = dt_obj['dateTime'].replace('Z', '+00:00')
        try:
            return datetime.fromisoformat(dt_str)
        except Exception:
            # Fallback: strip timezone if parsing fails
            return datetime.fromisoformat(dt_str.split('+')[0])
    if 'date' in dt_obj and dt_obj['date']:
        try:
            return datetime.fromisoformat(dt_obj['date'])
        except Exception:
            # yyyy-mm-dd
            return datetime.strptime(dt_obj['date'], '%Y-%m-%d')
    return None


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return not (a_end <= b_start or a_start >= b_end)


def _same_day(dt: datetime, day: datetime) -> bool:
    return dt.date() == day.date()


def _find_conflicts_same_name(
    events: List[Dict[str, Any]],
    target_start: datetime,
    target_end: datetime,
    summary: str,
    day_ref: datetime
) -> List[Tuple[datetime, datetime]]:
    base = _base_name(summary)
    conflicts: List[Tuple[datetime, datetime]] = []
    for e in events:
        s = (e.get('summary') or e.get('title') or '').strip()
        if not s:
            continue
        if _base_name(s) != base:
            continue
        es = _parse_event_dt(e.get('start', {}))
        ee = _parse_event_dt(e.get('end', {}))
        if not es or not ee:
            continue
        # Keep only same-day events
        if not _same_day(es, day_ref):
            continue
        if _overlaps(target_start, target_end, es, ee):
            conflicts.append((es, ee))
    return conflicts


def execute(data: Dict[str, Any] = None, tools: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Workflow: crée un événement le lendemain à une heure aléatoire.

    Règles de conflit (même nom):
    - Si le créneau ciblé est pris par le même nom, placer l'événement "à la suite".
    - Si ce nouveau créneau est encore pris par le même nom, garder le créneau initial
      et ajouter/remplacer un suffixe de 6 chiffres au nom.
    """
    params = data or {}

    # Inputs with sensible defaults
    summary = params.get('summary', 'Rendez-vous')
    duration_minutes = int(params.get('duration_minutes', 60))
    day_offset = int(params.get('day_offset', 1))  # 1 = demain
    hour_start = int(params.get('hour_start', 8))  # borne incluse
    hour_end = int(params.get('hour_end', 18))     # borne incluse
    calendar_id = params.get('calendar_id')
    description = params.get('description', 'Créé automatiquement par workflow: Evénement aléatoire demain')

    # Tools
    date_tool = tools.get('date') if tools else DateTool()
    calendar_tool = tools.get('calendar') if tools else CalendarTool()

    def open_oauth_and_wait(timeout_sec: int = 45, poll_interval: float = 1.5) -> str:
        """Open OAuth page and wait up to timeout for completion. Returns the auth_url used."""
        try:
            status = calendar_tool.get_oauth_status()
            auth_path = status.get('auth_url', '/oauth/calendar/auth')
            base = calendar_tool.config.get('oauth_url') or f"http://{settings.host}:{settings.port}"
            auth_url_local = auth_path if auth_path.startswith('http') else f"{base}{auth_path}"
        except Exception:
            auth_url_local = f"http://{settings.host}:{settings.port}/oauth/calendar/auth"
        try:
            webbrowser.open(auth_url_local)
        except Exception:
            pass
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            if calendar_tool.authenticate():
                break
            time.sleep(poll_interval)
        return auth_url_local

    # Authenticate tools; if calendar auth fails, open OAuth and wait briefly
    date_ok = date_tool.authenticate()
    cal_ok = calendar_tool.authenticate()
    if not date_ok:
        return {"status": "error", "message": "Date tool authentication failed"}
    if not cal_ok:
        auth_url = open_oauth_and_wait()
        if not calendar_tool.authenticate():
            return {
                "status": "error",
                "message": "Calendar not authenticated. OAuth page opened.",
                "data": {"oauth_required": True, "auth_url": auth_url}
            }

    # Compute tomorrow's date via DateTool
    date_res = date_tool.execute('calculate_date', {
        'days': day_offset,
        'format': '%Y-%m-%d'
    })
    if date_res.get('status') != 'success':
        return {"status": "error", "message": "Date tool failed", "data": date_res}

    target_date_str = date_res['data']['date']  # yyyy-mm-dd

    # Pick a random hour within [hour_start, hour_end]
    if hour_end < hour_start:
        hour_start, hour_end = hour_end, hour_start
    rand_hour = random.randint(hour_start, hour_end)

    start_dt = datetime.strptime(f"{target_date_str} {rand_hour:02d}:00:00", '%Y-%m-%d %H:%M:%S')
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    # Fetch upcoming events and filter for same day
    list_res = calendar_tool.execute('list_events', { 'count': 250, **({'calendar_id': calendar_id} if calendar_id else {}) })
    if list_res.get('status') != 'success':
        return {"status": "error", "message": "Failed to list calendar events", "data": list_res}

    events = list_res['data'].get('events', [])

    # 1) Check conflicts (same name) at the planned slot
    conflicts = _find_conflicts_same_name(events, start_dt, end_dt, summary, start_dt)

    chosen_start = start_dt
    chosen_end = end_dt
    chosen_summary = summary
    conflict_strategy = "none"

    if conflicts:
        # Place immediately after the last overlapping same-name event
        latest_end = max(ee for (_, ee) in conflicts)
        follow_start = latest_end
        follow_end = follow_start + timedelta(minutes=duration_minutes)

        conflicts_follow = _find_conflicts_same_name(events, follow_start, follow_end, summary, start_dt)
        if conflicts_follow:
            # Keep initial slot, add/replace 6-digit suffix
            chosen_start = start_dt
            chosen_end = end_dt
            chosen_summary = _with_random_suffix(summary)
            conflict_strategy = "initial_with_suffix"
        else:
            chosen_start = follow_start
            chosen_end = follow_end
            chosen_summary = summary
            conflict_strategy = "follow_slot"
    else:
        conflict_strategy = "no_conflict"

    # Ensure suffix replacement if summary already had one and we chose to add suffix
    if conflict_strategy == "initial_with_suffix":
        # already handled by _with_random_suffix (it replaces if present)
        pass

    # Create event
    payload = {
        'summary': chosen_summary,
        'start_time': chosen_start.strftime('%Y-%m-%dT%H:%M:%S'),
        'end_time': chosen_end.strftime('%Y-%m-%dT%H:%M:%S'),
        'description': description
    }
    if calendar_id:
        payload['calendar_id'] = calendar_id

    create_res = calendar_tool.execute('create_event', payload)
    if create_res.get('status') != 'success':
        # If insufficient permissions or auth error, open OAuth page, wait, then retry once
        error_text = str(create_res)
        need_oauth = any(s in error_text for s in [
            'insufficientPermissions', 'Insufficient Permission', 'Not authenticated', 'invalid_grant'
        ])
        auth_url = None
        if need_oauth:
            auth_url = open_oauth_and_wait()
            if calendar_tool.authenticate():
                retry_res = calendar_tool.execute('create_event', payload)
                if retry_res.get('status') == 'success':
                    create_res = retry_res
        if create_res.get('status') != 'success':
            return {
                "status": "error",
                "message": "Failed to create event",
                "data": {
                    "params": params,
                    "payload": payload,
                    "strategy": conflict_strategy,
                    "error": create_res,
                    **({"oauth_required": True, "auth_url": auth_url} if auth_url else {})
                }
            }

    return {
        "status": "success",
        "message": f"Evénement créé: {chosen_summary} - {payload['start_time']}",
        "data": {
            "chosen_summary": chosen_summary,
            "start": payload['start_time'],
            "end": payload['end_time'],
            "strategy": conflict_strategy,
            "base_summary": _base_name(summary),
            "target_date": target_date_str,
            "random_hour": rand_hour,
            "duration_minutes": duration_minutes,
            "calendar_result": create_res
        }
    }


def validate_data(data: Dict[str, Any]) -> bool:
    # Accept all; optional types validation
    try:
        if 'duration_minutes' in data:
            int(data['duration_minutes'])
        if 'hour_start' in data:
            int(data['hour_start'])
        if 'hour_end' in data:
            int(data['hour_end'])
        if 'day_offset' in data:
            int(data['day_offset'])
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # Local test
    res = execute({
        # 'summary': 'Rendez-vous de test',
        # 'duration_minutes': 45,
        # 'hour_start': 9,
        # 'hour_end': 17
    })
    print(res)

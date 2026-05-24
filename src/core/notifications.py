import datetime
import uuid
import threading
from collections import OrderedDict

NOTIF_CATEGORIES = {
    "security":   {"icon": "🛡️", "color": "#8a2a2a"},
    "system":     {"icon": "⚙️", "color": "#2a6a8a"},
    "learning":   {"icon": "📚", "color": "#2a8a5a"},
    "task":       {"icon": "📋", "color": "#8a6a2a"},
    "network":    {"icon": "🌐", "color": "#4a6a8a"},
    "general":    {"icon": "ℹ️", "color": "#6a6a6a"},
}

NOTIF_PRIORITIES = {
    "critical": {"weight": 4, "label": "CRÍTICO"},
    "high":     {"weight": 3, "label": "ALTA"},
    "normal":   {"weight": 2, "label": "Normal"},
    "low":      {"weight": 1, "label": "Baja"},
}


class Notification:
    __slots__ = ("id", "title", "message", "category", "priority",
                 "timestamp", "read", "source", "action_data")

    def __init__(self, title, message, category="general", priority="normal",
                 source="", action_data=None):
        self.id = uuid.uuid4().hex[:12]
        self.title = title
        self.message = message
        self.category = category if category in NOTIF_CATEGORIES else "general"
        self.priority = priority if priority in NOTIF_PRIORITIES else "normal"
        self.timestamp = datetime.datetime.now()
        self.read = False
        self.source = source
        self.action_data = action_data or {}

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "priority": self.priority,
            "timestamp": self.timestamp.isoformat(),
            "read": self.read,
            "source": self.source,
        }

    @property
    def category_icon(self):
        return NOTIF_CATEGORIES.get(self.category, {}).get("icon", "ℹ️")

    @property
    def category_color(self):
        return NOTIF_CATEGORIES.get(self.category, {}).get("color", "#6a6a6a")

    @property
    def priority_weight(self):
        return NOTIF_PRIORITIES.get(self.priority, {}).get("weight", 2)

    @property
    def time_ago(self):
        delta = datetime.datetime.now() - self.timestamp
        if delta.days > 0:
            return f"hace {delta.days}d"
        if delta.seconds >= 3600:
            return f"hace {delta.seconds // 3600}h"
        if delta.seconds >= 60:
            return f"hace {delta.seconds // 60}m"
        return "ahora"


class NotificationManager:
    def __init__(self, max_history=500):
        self._lock = threading.Lock()
        self._notifications = OrderedDict()
        self._max_history = max_history
        self._callbacks = []

    def add_notification(self, title, message, category="general",
                         priority="normal", source="", action_data=None):
        notif = Notification(title, message, category, priority, source, action_data)
        with self._lock:
            self._notifications[notif.id] = notif
            if len(self._notifications) > self._max_history:
                oldest = next(iter(self._notifications))
                del self._notifications[oldest]
        self._notify_callbacks(notif)
        return notif

    def get_notifications(self, category=None, unread_only=False, limit=50, offset=0):
        with self._lock:
            items = list(self._notifications.values())
        if category:
            items = [n for n in items if n.category == category]
        if unread_only:
            items = [n for n in items if not n.read]
        items.sort(key=lambda n: n.timestamp, reverse=True)
        return items[offset:offset + limit]

    def get_unread_count(self):
        with self._lock:
            return sum(1 for n in self._notifications.values() if not n.read)

    def get_unread_by_category(self):
        with self._lock:
            counts = {}
            for n in self._notifications.values():
                if not n.read:
                    counts[n.category] = counts.get(n.category, 0) + 1
            return counts

    def mark_read(self, notif_id):
        with self._lock:
            if notif_id in self._notifications:
                self._notifications[notif_id].read = True
                return True
            return False

    def mark_all_read(self, category=None):
        with self._lock:
            for n in self._notifications.values():
                if category is None or n.category == category:
                    n.read = True

    def mark_all_read_for_source(self, source):
        with self._lock:
            for n in self._notifications.values():
                if n.source == source:
                    n.read = True

    def clear(self, category=None):
        with self._lock:
            if category:
                self._notifications = OrderedDict(
                    (k, v) for k, v in self._notifications.items()
                    if v.category != category
                )
            else:
                self._notifications.clear()

    def on_notification(self, callback):
        self._callbacks.append(callback)

    def _notify_callbacks(self, notif):
        for cb in self._callbacks:
            try:
                cb(notif)
            except Exception:
                pass

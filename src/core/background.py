import threading
import time
import uuid
import datetime
from collections import OrderedDict


class BackgroundProcess:
    __slots__ = ("id", "name", "status", "progress", "message", "result",
                 "error", "created_at", "started_at", "completed_at",
                 "cancellable", "_cancel", "meta")

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    def __init__(self, name, cancellable=True, meta=None):
        self.id = uuid.uuid4().hex[:12]
        self.name = name
        self.status = self.STATUS_PENDING
        self.progress = 0.0
        self.message = ""
        self.result = None
        self.error = None
        self.created_at = datetime.datetime.now()
        self.started_at = None
        self.completed_at = None
        self.cancellable = cancellable
        self._cancel = threading.Event()
        self.meta = meta or {}

    def cancel(self):
        if self.cancellable:
            self._cancel.set()
            return True
        return False

    @property
    def is_cancelled(self):
        return self._cancel.is_set()

    @property
    def duration(self):
        start = self.started_at or self.created_at
        end = self.completed_at or datetime.datetime.now()
        return (end - start).total_seconds()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "cancellable": self.cancellable,
        }


class ProcessManager:
    def __init__(self, max_concurrent=4, notify_callback=None):
        self._processes = OrderedDict()
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max_concurrent)
        self._worker_group = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._worker_group.start()
        self._notify = notify_callback

    def start(self, name, target_fn, args=(), kwargs=None, cancellable=True, meta=None):
        if kwargs is None:
            kwargs = {}
        proc = BackgroundProcess(name, cancellable, meta)
        with self._lock:
            self._processes[proc.id] = proc
        self._semaphore.acquire()
        t = threading.Thread(target=self._run_wrapper, args=(proc, target_fn, args, kwargs),
                             daemon=True, name=f"bg-{proc.id[:8]}")
        t.start()
        return proc.id

    def _run_wrapper(self, proc, fn, args, kwargs):
        try:
            proc.status = BackgroundProcess.STATUS_RUNNING
            proc.started_at = datetime.datetime.now()
            fn(proc, *args, **kwargs)
            if proc.is_cancelled:
                proc.status = BackgroundProcess.STATUS_CANCELLED
            else:
                proc.status = BackgroundProcess.STATUS_COMPLETED
                proc.progress = 100.0
        except Exception as e:
            proc.status = BackgroundProcess.STATUS_FAILED
            proc.error = str(e)
            import traceback
            proc.error += "\n" + traceback.format_exc()
        finally:
            proc.completed_at = datetime.datetime.now()
            self._semaphore.release()
            if self._notify:
                try:
                    self._notify(proc)
                except Exception:
                    pass

    def cancel(self, proc_id):
        with self._lock:
            proc = self._processes.get(proc_id)
        if proc:
            return proc.cancel()
        return False

    def get(self, proc_id):
        with self._lock:
            return self._processes.get(proc_id)

    def list(self, status=None, limit=50):
        with self._lock:
            items = list(self._processes.values())
        if status:
            items = [p for p in items if p.status == status]
        items.sort(key=lambda p: p.created_at, reverse=True)
        return items[:limit]

    def list_active(self):
        return self.list(status=BackgroundProcess.STATUS_RUNNING)

    def cleanup(self, max_age=3600):
        now = datetime.datetime.now()
        with self._lock:
            to_remove = []
            for pid, p in self._processes.items():
                if p.status in (BackgroundProcess.STATUS_COMPLETED,
                                BackgroundProcess.STATUS_FAILED,
                                BackgroundProcess.STATUS_CANCELLED):
                    if p.completed_at and (now - p.completed_at).total_seconds() > max_age:
                        to_remove.append(pid)
            for pid in to_remove:
                del self._processes[pid]
            return len(to_remove)

    def _cleanup_loop(self):
        while True:
            time.sleep(300)
            try:
                self.cleanup(3600)
            except Exception:
                pass

    def update_progress(self, proc_id, progress, message=None):
        with self._lock:
            proc = self._processes.get(proc_id)
        if proc:
            proc.progress = min(100.0, max(0.0, progress))
            if message:
                proc.message = message

    def update_message(self, proc_id, message):
        with self._lock:
            proc = self._processes.get(proc_id)
        if proc:
            proc.message = message

    def set_result(self, proc_id, result):
        with self._lock:
            proc = self._processes.get(proc_id)
        if proc:
            proc.result = result

    def running_count(self):
        with self._lock:
            return sum(1 for p in self._processes.values()
                       if p.status == BackgroundProcess.STATUS_RUNNING)

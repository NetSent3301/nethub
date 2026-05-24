"""
Sistema de eventos pub/sub para NetHUB Ultimate.
Permite a módulos y componentes comunicarse sin acoplamiento directo.
"""
import threading
from .logger import get_logger

logger = get_logger("events")


class EventBus:
    def __init__(self):
        self._subscribers = {}
        self._lock = threading.Lock()

    def subscribe(self, event, callback, module=None):
        if not callable(callback):
            raise TypeError("callback debe ser callable")
        with self._lock:
            if event not in self._subscribers:
                self._subscribers[event] = []
            self._subscribers[event].append({
                "callback": callback,
                "module": module or callback.__module__,
            })
            logger.debug("Suscripcion al evento '%s' desde %s", event, module or callback.__module__)

    def unsubscribe(self, event, callback):
        with self._lock:
            if event not in self._subscribers:
                return
            self._subscribers[event] = [
                s for s in self._subscribers[event]
                if s["callback"] is not callback
            ]
            if not self._subscribers[event]:
                del self._subscribers[event]

    def subscribe_module(self, module, event_map):
        for event, method_name in event_map.items():
            callback = getattr(module, method_name, None)
            if callback and callable(callback):
                self.subscribe(event, callback, module=module.__class__.__name__)

    def emit(self, event, **data):
        with self._lock:
            callbacks = list(self._subscribers.get(event, []))
        if not callbacks:
            logger.debug("Evento '%s' emitido sin suscriptores", event)
            return
        logger.debug("Evento '%s' -> %d suscriptores", event, len(callbacks))
        for sub in callbacks:
            try:
                sub["callback"](event=event, **data)
            except Exception:
                logger.error("Error en handler del evento '%s' en %s",
                             event, sub["module"], exc_info=True)

    def emit_async(self, event, **data):
        thread = threading.Thread(target=self.emit, args=(event,), kwargs=data, daemon=True)
        thread.start()

    def clear(self):
        with self._lock:
            self._subscribers.clear()
        logger.debug("EventBus limpiado")

    @property
    def events(self):
        with self._lock:
            return dict(self._subscribers)

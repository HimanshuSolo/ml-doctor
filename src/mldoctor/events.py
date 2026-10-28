"""In-process pipeline events: ordered, JSON-serialisable, SSE-ready."""
import time


class EventBus:
    def __init__(self, listeners=None):
        self.events = []
        self.listeners = list(listeners or [])

    def subscribe(self, fn):
        self.listeners.append(fn)
        return fn

    def emit(self, type, **data):
        ev = {"seq": len(self.events), "ts": time.time(), "type": type, **data}
        self.events.append(ev)
        for fn in self.listeners:
            fn(ev)
        return ev

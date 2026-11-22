import copy
import threading


class MQTTBroker:
    def __init__(self):
        self._retained = {}
        self._subscribers = {}
        self._counters = {}
        self._lock = threading.RLock()

    def subscribe(self, topic, callback):
        with self._lock:
            self._subscribers.setdefault(topic, []).append(callback)
            if topic in self._retained:
                callback(topic, copy.deepcopy(self._retained[topic]))

    def publish(self, topic, payload):
        with self._lock:
            self._counters[topic] = self._counters.get(topic, 0) + 1
            self._retained[topic] = copy.deepcopy(payload)
            callbacks = list(self._subscribers.get(topic, ()))
        for callback in callbacks:
            callback(topic, copy.deepcopy(payload))

    def retained(self, topic):
        with self._lock:
            return copy.deepcopy(self._retained.get(topic))

    def count(self, topic=None):
        with self._lock:
            if topic is not None:
                return self._counters.get(topic, 0)
            return sum(self._counters.values())

    def topics(self):
        with self._lock:
            return sorted(set(self._retained) | set(self._counters))

    def clear(self):
        with self._lock:
            self._retained.clear()
            self._subscribers.clear()
            self._counters.clear()

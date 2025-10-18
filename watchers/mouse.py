# watchers/mouse_watcher.py
import threading
from Xlib import X, display
from Xlib.ext import record
from Xlib.protocol import rq

from . import Watcher

class MouseWatcher(Watcher):
    METRIC_KEYS = {
        'mouse.clicks.total',
        'mouse.clicks.primary',
        'mouse.clicks.secondary',
        'mouse.clicks.middle',
        'mouse.scroll.up',
        'mouse.scroll.down',
        'mouse.scroll.left',
        'mouse.scroll.right',
        'mouse.movement.x',
        'mouse.movement.y',
    }

    def __init__(self):
        self._lock = threading.Lock()
        self._total_dx = 0
        self._total_dy = 0
        self._last_x = None
        self._last_y = None

    def _handle_event(self, event, store):
        with self._lock:
            # Handle motion
            if event.type == X.MotionNotify:
                if self._last_x is not None and self._last_y is not None:
                    dx = abs(event.root_x - self._last_x)
                    dy = abs(event.root_y - self._last_y)
                    self._total_dx += dx
                    self._total_dy += dy
                self._last_x = event.root_x
                self._last_y = event.root_y

            # Handle button press
            elif event.type == X.ButtonPress:
                button = event.detail

                # Write to shared store (under store's lock!)
                with store.lock:
                    store.metrics['mouse.clicks.total'] += 1
                    if button == 1:
                        store.metrics['mouse.clicks.primary'] += 1
                    elif button == 3:
                        store.metrics['mouse.clicks.secondary'] += 1
                    elif button == 2:
                        store.metrics['mouse.clicks.middle'] += 1

                    # Scroll: 4/5 = vertical, 6/7 = horizontal
                    # Replace the old scroll block with this:
                    if button == 4:
                        store.metrics['mouse.scroll.up'] += 1
                    elif button == 5:
                        store.metrics['mouse.scroll.down'] += 1
                    elif button == 6:
                        store.metrics['mouse.scroll.left'] += 1
                    elif button == 7:
                        store.metrics['mouse.scroll.right'] += 1

    def _flush_movement(self, store):
        """Periodically flush accumulated movement to shared store"""
        while True:
            with self._lock:
                dx, dy = self._total_dx, self._total_dy
                self._total_dx = 0
                self._total_dy = 0

            if dx != 0 or dy != 0:
                with store.lock:
                    store.metrics['mouse.movement.x'] += dx
                    store.metrics['mouse.movement.y'] += dy

            threading.Event().wait(1)  # Sleep 1s without blocking GIL harshly

    def start(self, store):
        # Start movement flusher
        flush_thread = threading.Thread(target=self._flush_movement, args=(store,), daemon=True)
        flush_thread.start()

        # Start X11 recorder
        def record_thread():
            d = display.Display()
            root = d.screen().root

            def callback(reply):
                if reply.category != record.FromServer or reply.client_swapped:
                    return
                if not reply.data or len(reply.data) < 2:
                    return

                data = reply.data
                while data:
                    event, data = rq.EventField(None).parse_binary_value(
                        data, d.display, None, None
                    )
                    self._handle_event(event, store)

            ctx = d.record_create_context(
                0,
                [record.AllClients],
                [{
                    'core_requests': (0, 0),
                    'core_replies': (0, 0),
                    'ext_requests': (0, 0, 0, 0),
                    'ext_replies': (0, 0, 0, 0),
                    'delivered_events': (0, 0),
                    'device_events': (X.ButtonPress, X.MotionNotify),
                    'errors': (0, 0),
                    'client_started': False,
                    'client_died': False,
                }]
            )
            d.record_enable_context(ctx, callback)
            d.record_free_context(ctx)

        recorder = threading.Thread(target=record_thread, daemon=True)
        recorder.start()
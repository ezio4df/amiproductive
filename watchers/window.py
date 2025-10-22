import threading
from Xlib import X, Xatom, display
from . import Watcher


class WindowWatcher(Watcher):
    METRIC_KEYS = {
        'window.focus_events': []
    }

    @staticmethod
    def _get_window_title(win):
        try:
            prop = win.get_property(Xatom.WM_NAME, X.AnyPropertyType, 0, 1000)
            if not prop or not prop.value:
                return "[no title]"

            prop_type = prop.property_type
            UTF8_STRING = win.display.get_atom("UTF8_STRING")
            COMPOUND_TEXT = win.display.get_atom("COMPOUND_TEXT")

            if prop_type == UTF8_STRING:
                return prop.value.decode('utf-8')
            elif prop_type == Xatom.STRING:
                return prop.value.decode('iso-8859-1')
            elif prop_type == COMPOUND_TEXT:
                try:
                    prop2 = win.get_property(Xatom.WM_NAME, Xatom.STRING, 0, 1000)
                    if prop2 and prop2.value:
                        return prop2.value.decode('iso-8859-1')
                except Exception:
                    pass
                return prop.value.decode('iso-8859-1', errors='replace')
            else:
                return prop.value.decode('utf-8', errors='replace')
        except Exception:
            return "[error]"

    @staticmethod
    def _get_wm_class_instance(win):
        try:
            cls = win.get_wm_class()
            return cls[0].lower() if cls else "unknown"
        except Exception:
            return "unknown"

    def start(self, store):
        # Run the X11 event loop in a daemon thread
        watcher_thread = threading.Thread(
            target=self._x11_event_loop,
            args=(store,),
            daemon=True,
            name="WindowWatcher-X11"
        )
        watcher_thread.start()

    def _x11_event_loop(self, store):
        d = display.Display()
        try:
            root = d.screen().root
            NET_ACTIVE_WINDOW = d.intern_atom('_NET_ACTIVE_WINDOW')
            root.change_attributes(event_mask=X.PropertyChangeMask)

            last_win_id = None  # track last focused window

            while True:
                ev = d.next_event()
                if ev.type == X.PropertyNotify and ev.atom == NET_ACTIVE_WINDOW:
                    prop = root.get_full_property(NET_ACTIVE_WINDOW, X.AnyPropertyType)
                    if not (prop and prop.value and len(prop.value) > 0):
                        continue
                    win_id = prop.value[0]
                    if not win_id or win_id == last_win_id:  # skip if same as before
                        continue

                    last_win_id = win_id  # update last

                    try:
                        win = d.create_resource_object('window', win_id)
                        app = self._get_wm_class_instance(win)
                        title = self._get_window_title(win)

                        with store.lock:
                            for ev in store.metrics['window.focus_events']:
                                if ev[0] == app and ev[1] == title:
                                    ev[3] += 1
                                    break
                            else:
                                store.metrics['window.focus_events'].append([app, title, 1])

                    except Exception:
                        pass  # silent fail on bad windows

        except Exception:
            pass
        finally:
            d.close()

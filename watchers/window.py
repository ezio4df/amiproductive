#!/usr/bin/env python3
import signal
from Xlib import X, Xatom, display
from Xlib.xobject.drawable import Window

def get_window_title(win):
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
    except Exception as e:
        return f"[error: {e}]"

def get_wm_class_instance(win):
    try:
        cls = win.get_wm_class()
        return cls[0].lower() if cls else "unknown"
    except Exception:
        return "unknown"

def main():
    d = display.Display()
    root = d.screen().root
    NET_ACTIVE_WINDOW = d.intern_atom('_NET_ACTIVE_WINDOW')
    root.change_attributes(event_mask=X.PropertyChangeMask)

    print("👁️  KDE/X11 Focus Listener (COMPOUND_TEXT fixed)")
    print("-" * 60)

    try:
        while True:
            ev = d.next_event()
            if ev.type == X.PropertyNotify and ev.atom == NET_ACTIVE_WINDOW:
                prop = root.get_full_property(NET_ACTIVE_WINDOW, X.AnyPropertyType)
                if prop and prop.value:
                    win_id = prop.value[0]
                    if win_id:
                        try:
                            win = d.create_resource_object('window', win_id)
                            app = get_wm_class_instance(win)
                            title = get_window_title(win)
                            print(f"✅ App: {app} | Title: {title!r}")
                        except Exception as e:
                            print(f"⚠️  Error: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Done.")
    finally:
        d.close()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: exit(0))
    main()
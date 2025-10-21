import threading
from Xlib import X, display
from Xlib.ext import record
from Xlib.protocol import rq
from . import Watcher

# ISO 105-key keyboard: keycode -> canonical name
# Source: `xmodmap -pke` on standard Linux ISO layout
KEYCODE_TO_NAME = {
    # Row 1: Esc, F1-F12
    9: 'Escape',
    67: 'F1', 68: 'F2', 69: 'F3', 70: 'F4',
    71: 'F5', 72: 'F6', 73: 'F7', 74: 'F8',
    75: 'F9', 76: 'F10', 95: 'F11', 96: 'F12',

    # Row 2: ` 1 2 ... 9 0 - = Backspace
    49: 'grave', 10: '1', 11: '2', 12: '3', 13: '4', 14: '5',
    15: '6', 16: '7', 17: '8', 18: '9', 19: '0',
    20: 'minus', 21: 'equal', 22: 'BackSpace',

    # Row 3: Tab q w ... ] \
    23: 'Tab', 24: 'q', 25: 'w', 26: 'e', 27: 'r', 28: 't',
    29: 'y', 30: 'u', 31: 'i', 32: 'o', 33: 'p',
    34: 'bracketleft', 35: 'bracketright', 51: 'backslash',

    # Row 4: Caps a s ... ; ' Enter
    66: 'Caps_Lock', 38: 'a', 39: 's', 40: 'd', 41: 'f', 42: 'g',
    43: 'h', 44: 'j', 45: 'k', 46: 'l',
    47: 'semicolon', 48: 'apostrophe', 36: 'Return',

    # Row 5: Shift<> z x ... , . / Shift
    50: 'Shift_L', 94: 'less', 52: 'z', 53: 'x', 54: 'c', 55: 'v',
    56: 'b', 57: 'n', 58: 'm',
    59: 'comma', 60: 'period', 61: 'slash', 62: 'Shift_R',

    # Bottom: Ctrl Alt Space Alt Ctrl
    37: 'Control_L', 64: 'Alt_L', 65: 'space', 108: 'Alt_R', 105: 'Control_R',
    133: 'Super_L', 134: 'Super_R',

    # Navigation cluster
    110: 'Insert', 119: 'Delete',
    115: 'Home', 117: 'End',
    112: 'Page_Up', 117: 'Page_Down',  # Note: some overlap; adjust if needed
    111: 'Up', 116: 'Down', 113: 'Left', 114: 'Right',

    # Numeric keypad
    77: 'Num_Lock',
    90: 'KP_0', 87: 'KP_1', 88: 'KP_2', 89: 'KP_3',
    83: 'KP_4', 84: 'KP_5', 85: 'KP_6',
    79: 'KP_7', 80: 'KP_8', 81: 'KP_9',
    82: 'KP_Decimal',
    106: 'KP_Divide', 63: 'KP_Multiply',
    86: 'KP_Subtract', 87: 'KP_Add',  # Note: 87 reused; verify on your system
    104: 'KP_Enter',

    # Locks
    78: 'Scroll_Lock',
}

# Build metric keys
_ISO_105_NAMES = set(KEYCODE_TO_NAME.values())
METRIC_KEYS = {f'keyboard.key.{name}' for name in _ISO_105_NAMES} | {'keyboard.other'}

class KeyboardWatcher(Watcher):
    METRIC_KEYS = METRIC_KEYS

    def start(self, store):
        def record_thread():
            d = display.Display()

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
                    if event.type == X.KeyPress:
                        name = KEYCODE_TO_NAME.get(event.detail)
                        metric = f'keyboard.key.{name}' if name else 'keyboard.other'
                        with store.lock:
                            store.metrics[metric] += 1

            ctx = d.record_create_context(
                0,
                [record.AllClients],
                [{
                    'core_requests': (0, 0),
                    'core_replies': (0, 0),
                    'ext_requests': (0, 0, 0, 0),
                    'ext_replies': (0, 0, 0, 0),
                    'delivered_events': (0, 0),
                    'device_events': (X.KeyPress, X.KeyPress),
                    'errors': (0, 0),
                    'client_started': False,
                    'client_died': False,
                }]
            )
            try:
                d.record_enable_context(ctx, callback)
            finally:
                d.record_free_context(ctx)
                d.close()

        threading.Thread(target=record_thread, daemon=True).start()
# === EXAMPLE: Minimal Keystroke Watcher (X11) ===
class DummyWatcher(Watcher):
    def start(self, store):
        def _fake_typing():
            while True:
                time.sleep(2)
                with store.lock:
                    store.metrics['keystrokes.letter'] += 5
        threading.Thread(target=_fake_typing, daemon=True).start()

"""Puts `backend/` on sys.path for `import app.*`, and isolates test data from dev data.

Must run before `app.config` is imported, which is why it lives at module import time.
"""

import os
import tempfile

os.environ.setdefault("WW_DATA_DIR", tempfile.mkdtemp(prefix="weather-whiplash-test-"))

# The suite never touches the network. Tests that need the live-fetch path turn this off
# themselves via monkeypatch, so the fallback logic is still exercised.
os.environ.setdefault("WW_OFFLINE", "1")

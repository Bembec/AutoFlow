"""Shared pytest setup: keep test data out of the real data folder."""

import os
import tempfile

# Must be set before any autoflow module is imported
os.environ.setdefault("AUTOFLOW_DATA_DIR", tempfile.mkdtemp(prefix="autoflow-test-"))
os.environ["AI_CLASSIFICATION_ENABLED"] = "false"
os.environ["EMAIL_SEND_ENABLED"] = "false"

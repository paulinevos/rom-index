"""Shared test setup: `mpos` only exists on the device, so it is stubbed here.

Every test module imports this first, so the stub is installed once and all
modules see the same fake regardless of discovery order.
"""

import sys
import types
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "com.paulinevos.rom_installer"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))


class FakeDownloadManager:
    """Stands in for mpos.DownloadManager, reproducing its error contract:
    every non-2xx response surfaces as RuntimeError("HTTP nnn")."""

    raises = None
    returns = b""

    @classmethod
    async def download_url(cls, url, redact_url=False, **kwargs):
        if cls.raises:
            raise cls.raises
        return cls.returns

    @classmethod
    def reset(cls):
        cls.raises = None
        cls.returns = b""


_mpos = types.ModuleType("mpos")
_mpos.DownloadManager = FakeDownloadManager
sys.modules["mpos"] = _mpos

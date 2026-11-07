"""Build the Home Hub starter backup.

The result is an ordinary Home Assistant backup that a new house restores from
the welcome screen ("Upload backup"). It holds only the add-ons and cards Home
Hub needs, with no accounts, devices or settings from anyone's house, so after
restoring Home Assistant asks the family to create their own login.

    python3 starter/build_starter.py

Inputs (see README): custom_components/home_hub, the four cards in
test-ha/config/www, and HACS and browser_mod unpacked in starter/downloads.
"""

from __future__ import annotations

from datetime import datetime, timezone
import io
import json
from pathlib import Path
import secrets
import tarfile

ROOT = Path(__file__).resolve().parent.parent
HA_VERSION = "2026.6.0"
CARDS = ("button-card.js", "mushroom.js", "card-mod.js", "wallpanel.js")

CONFIGURATION_YAML = """\
# Home Hub starter. Add your own settings below as you need them.
default_config:

frontend:
  themes: !include_dir_merge_named themes
"""


def _sources() -> dict[str, Path]:
    """Folder name in the backup -> where it comes from."""
    browser_mod = next((ROOT / "starter/downloads/browser_mod/unzipped").glob("*/custom_components/browser_mod"))
    return {
        "custom_components/home_hub": ROOT / "custom_components/home_hub",
        "custom_components/home_hub_checkin": ROOT / "extras/custom_components/home_hub_checkin",
        "custom_components/hacs": ROOT / "starter/downloads/hacs/unzipped",
        "custom_components/browser_mod": browser_mod,
    }


def _resources() -> bytes:
    items = [{"id": secrets.token_hex(16), "url": f"/local/{card}", "type": "module"} for card in CARDS]
    store = {"version": 1, "minor_version": 1, "key": "lovelace_resources", "data": {"items": items}}
    return json.dumps(store, indent=2).encode()


def _add_bytes(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o644
    info.mtime = int(datetime.now(timezone.utc).timestamp())
    tar.addfile(info, io.BytesIO(data))


def _skip(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    if "__pycache__" in info.name or info.name.endswith((".pyc", ".DS_Store")):
        return None
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    return info


def build(out: Path) -> Path:
    config = io.BytesIO()
    with tarfile.open(fileobj=config, mode="w:gz") as tar:
        _add_bytes(tar, "data/configuration.yaml", CONFIGURATION_YAML.encode())
        _add_bytes(tar, "data/.HA_VERSION", HA_VERSION.encode())
        _add_bytes(tar, "data/themes/.keep", b"")
        _add_bytes(tar, "data/.storage/lovelace_resources", _resources())
        for name, source in _sources().items():
            tar.add(source, arcname=f"data/{name}", filter=_skip)
        for card in CARDS:
            tar.add(ROOT / "test-ha/config/www" / card, arcname=f"data/www/{card}", filter=_skip)

    now = datetime.now(timezone.utc)
    slug = secrets.token_hex(4)
    meta = {
        "compressed": True,
        "date": now.isoformat(),
        "extra": {"with_automatic_settings": False},
        "homeassistant": {"exclude_database": True, "version": HA_VERSION},
        "name": "Home Hub starter",
        "protected": False,
        "slug": slug,
        "type": "partial",
        "version": 2,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out, mode="w") as tar:
        _add_bytes(tar, "./backup.json", json.dumps(meta).encode())
        _add_bytes(tar, "homeassistant.tar.gz", config.getvalue())
    return out


if __name__ == "__main__":
    path = build(ROOT / "starter/dist/Home_Hub_starter.tar")
    print(f"Built {path} ({path.stat().st_size / 1e6:.1f} MB)")

from __future__ import annotations

import tomli
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Defaults:
    region: str = "부산 기장"
    property_type: str = "원룸"
    price_min: int = 0
    price_max: int = 2000000
    max_items: int = 50
    max_pages: int = 5


@dataclass
class BrowserCfg:

    headless: bool = True
    block_images: bool = True
    detail_pages_pool: int = 2


@dataclass
class PathsCfg:
    output: str = "output"
    logs: str = "logs"


@dataclass
class Settings:
    defaults: Defaults
    browser: BrowserCfg
    paths: PathsCfg
    append_mode: bool = False


def _load_settings() -> Settings:
    path = Path(__file__).with_name("settings.toml")
    if not path.exists():
        return Settings(Defaults(), BrowserCfg(), PathsCfg())
    data = tomli.loads(path.read_text("utf-8"))
    d = data.get("defaults", {})
    b = data.get("browser", {})
    p = data.get("paths", {})
    app = bool(data.get("append_mode", False))
    return Settings(
        Defaults(
            region=d.get("region", Defaults.region),
            property_type=d.get("property_type", Defaults.property_type),
            price_min=int(d.get("price_min", Defaults.price_min)),
            price_max=int(d.get("price_max", Defaults.price_max)),
            max_items=int(d.get("max_items", Defaults.max_items)),
            max_pages=int(d.get("max_pages", Defaults.max_pages)),
        ),
        BrowserCfg(
            headless=bool(b.get("headless", True)),
            block_images=bool(b.get("block_images", True)),
            detail_pages_pool=int(b.get("detail_pages_pool", 2)),
        ),
        PathsCfg(output=p.get("output", "output"), logs=p.get("logs", "logs")),
        append_mode=app,
    )


settings = _load_settings()



"""Frontend card and panel registration for Forecast Fusion.

Modeled after robust Home Assistant frontend registration patterns (ha_washdata).
"""

import logging
import os
from pathlib import Path
from typing import Any, cast

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

LOCAL_SUBDIR = "forecast_fusion_panel"
PANEL_JS_NAME = "forecast-fusion-panel.js"
PANEL_JS_URL = f"/{LOCAL_SUBDIR}/{PANEL_JS_NAME}"
PANEL_ELEMENT = "forecast-fusion-panel"
PANEL_URL_PATH = "forecast_fusion"
PANEL_REGISTERED_KEY = "forecast_fusion_panel_registered"
PANEL_STATIC_REGISTERED = "forecast_fusion_panel_static_registered"


def get_cache_buster() -> str:
    """Generate a stable cache buster based on panel JS file mtime."""
    try:
        src = Path(__file__).parent / "frontend" / PANEL_JS_NAME
        return str(int(os.path.getmtime(src)))
    except OSError:
        return "1"


def _register_static_path(hass: HomeAssistant, url_path: str, path: str) -> None:
    """Register a static path with HA HTTP component compatible across HA versions."""
    try:
        from homeassistant.components.http import StaticPathConfig

        if hasattr(hass.http, "async_register_static_paths"):

            async def _safe_register() -> None:
                try:
                    await hass.http.async_register_static_paths(
                        [StaticPathConfig(url_path, path, True)]
                    )
                except Exception as exc:
                    _LOGGER.debug(
                        "Failed to async register static path %s -> %s: %s",
                        url_path,
                        path,
                        exc,
                    )

            hass.async_create_task(_safe_register())
            return
    except Exception as exc:
        _LOGGER.debug("Async static path registration not available: %s", exc)

    try:
        http_obj = cast(Any, hass.http)
        register_static_path = getattr(http_obj, "register_static_path", None)
        if callable(register_static_path):
            register_static_path(url_path, path, cache_headers=True)
    except Exception as exc:
        _LOGGER.debug("Failed to register static path %s -> %s: %s", url_path, path, exc)


async def async_register_panel(hass: HomeAssistant) -> bool:
    """Serve forecast-fusion-panel.js and register a sidebar panel with Home Assistant."""
    if hass.data.get(PANEL_REGISTERED_KEY):
        return True

    src = Path(__file__).parent / "frontend" / PANEL_JS_NAME
    if not await hass.async_add_executor_job(src.exists):
        _LOGGER.warning("Panel JS not found at %s — sidebar panel not registered", src)
        return False

    if not hass.data.get(PANEL_STATIC_REGISTERED):
        hass.data[PANEL_STATIC_REGISTERED] = True
        try:
            try:
                from homeassistant.components.http import StaticPathConfig

                if hasattr(hass.http, "async_register_static_paths"):
                    await hass.http.async_register_static_paths(
                        [StaticPathConfig(PANEL_JS_URL, str(src), True)]
                    )
                else:
                    _register_static_path(hass, PANEL_JS_URL, str(src))
            except Exception as exc:
                _LOGGER.debug("Panel static path registration failed, falling back: %s", exc)
                _register_static_path(hass, PANEL_JS_URL, str(src))
        except Exception as exc:
            _LOGGER.warning("Forecast Fusion panel static path registration failed: %s", exc)
            hass.data.pop(PANEL_STATIC_REGISTERED, None)
            return False

    if hass.data.get(PANEL_REGISTERED_KEY):
        return True

    try:
        from homeassistant.components import frontend

        panel_version = await hass.async_add_executor_job(get_cache_buster)

        frontend.async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title="Forecast Fusion",
            sidebar_icon="mdi:weather-forecast-stat",
            frontend_url_path=PANEL_URL_PATH,
            config={
                "_panel_custom": {
                    "name": PANEL_ELEMENT,
                    "module_url": f"{PANEL_JS_URL}?v={panel_version}",
                    "embed_iframe": False,
                    "trust_external": False,
                }
            },
            require_admin=False,
        )
        hass.data[PANEL_REGISTERED_KEY] = True
        _LOGGER.info("Forecast Fusion sidebar panel registered at /%s", PANEL_URL_PATH)
        return True
    except Exception as exc:
        _LOGGER.warning("Failed to register Forecast Fusion panel: %s", exc)
        return False


async def async_unregister_panel(hass: HomeAssistant) -> None:
    """Tear down the Forecast Fusion sidebar panel."""
    if not hass.data.get(PANEL_REGISTERED_KEY) and not hass.data.get(PANEL_STATIC_REGISTERED):
        return

    if hass.data.get(PANEL_REGISTERED_KEY):
        try:
            from homeassistant.components import frontend

            frontend.async_remove_panel(hass, PANEL_URL_PATH)
            _LOGGER.info("Forecast Fusion sidebar panel removed from /%s", PANEL_URL_PATH)
        except Exception as exc:
            _LOGGER.debug("Failed to remove Forecast Fusion panel: %s", exc)

    hass.data.pop(PANEL_REGISTERED_KEY, None)
    hass.data.pop(PANEL_STATIC_REGISTERED, None)

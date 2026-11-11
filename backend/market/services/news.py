"""
Noticias recientes de un instrumento.

Fuentes (titulares + enlace a la nota original):
  1. Google Noticias RSS en español (Colombia).
  2. Yahoo Finance RSS (inglés) como respaldo.
Los resultados se guardan en caché 20 minutos. Sin internet se devuelve una lista vacía.
"""
import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import quote_plus

import requests
from django.core.cache import cache

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (AuraFarmers simulador educativo)"}
TTL = 20 * 60


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", unescape(text or ""))).strip()


def parse_rss(xml_text: str, default_source: str, limit: int = 12) -> list[dict]:
    items = []
    root = ET.fromstring(xml_text)
    for it in root.iter("item"):
        title = _clean(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        if not title or not link.startswith("http"):
            continue
        src_el = it.find("source")
        source = _clean(src_el.text) if src_el is not None and src_el.text else default_source
        # Google añade " - Fuente" al final del título
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        published = None
        raw_date = it.findtext("pubDate")
        if raw_date:
            try:
                published = parsedate_to_datetime(raw_date).isoformat()
            except (TypeError, ValueError):
                published = None
        items.append({"title": title, "url": link, "source": source, "published": published})
        if len(items) >= limit:
            break
    return items


def _google(query: str) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}+when:14d&hl=es-419&gl=CO&ceid=CO:es-419"
    r = requests.get(url, headers=HEADERS, timeout=6)
    r.raise_for_status()
    return parse_rss(r.text, "Google Noticias")


def _yahoo(symbol: str) -> list[dict]:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote_plus(symbol)}&region=US&lang=en-US"
    r = requests.get(url, headers=HEADERS, timeout=6)
    r.raise_for_status()
    return parse_rss(r.text, "Yahoo Finance")


def get_news(query: str, symbol: str | None = None) -> dict:
    key = "news:" + hashlib.md5(f"{symbol}|{query}".encode()).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return cached
    items, errors = [], 0
    for fetch, arg in ((_google, query), (_yahoo, symbol)):
        if not arg or items:
            continue
        try:
            items = fetch(arg)
        except Exception as exc:  # noqa: BLE001 — sin internet, bloqueo o XML inválido
            errors += 1
            log.info("Noticias no disponibles (%s): %s", fetch.__name__, exc)
    items.sort(key=lambda x: x["published"] or "", reverse=True)
    result = {"items": items, "available": bool(items) or errors == 0}
    cache.set(key, result, TTL if items else 120)
    return result

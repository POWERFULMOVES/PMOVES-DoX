from __future__ import annotations

import asyncio
import ipaddress
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import base64
import httpx
from urllib.parse import unquote_to_bytes

try:  # Optional dependency for rich cleaning
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore


def _run_async(coro):
    try:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            asyncio.set_event_loop(None)
            loop.close()
    except RuntimeError:
        return asyncio.run(coro)


async def _render_with_playwright(url: str, timeout: float) -> str:
    from playwright.async_api import async_playwright  # type: ignore

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
        html = await page.content()
        await browser.close()
        return html


def _clean_html(html: str) -> Tuple[str, Dict[str, Any]]:
    if not html:
        return "", {"cleaner": "none"}

    metadata: Dict[str, Any] = {"cleaner": "regex"}
    text = html

    if BeautifulSoup is not None:  # pragma: no branch - optional dep guard
        soup = BeautifulSoup(html, "html.parser")  # type: ignore[arg-type]
        for tag in soup(["script", "style", "noscript", "template"]):
            tag.decompose()
        text = soup.get_text("\n")
        metadata["cleaner"] = "beautifulsoup"
        metadata["title"] = soup.title.string.strip() if soup.title and soup.title.string else None
        metadata["links"] = [a.get("href") for a in soup.find_all("a") if a.get("href")]
    else:
        # Basic fallback: strip scripts/styles via regex
        text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)

    normalized = re.sub(r"\s+", " ", text).strip()
    metadata["word_count"] = len(normalized.split()) if normalized else 0
    return normalized, metadata


def _is_safe_url(url: str) -> Tuple[bool, str]:
    """Validate URL to prevent SSRF attacks.

    Returns:
        Tuple of (is_safe, error_message)
    """
    parsed = urlparse(url)

    # Only allow http/https and data schemes
    if parsed.scheme not in ["http", "https", "data"]:
        return False, f"Unsupported URL scheme: {parsed.scheme}. Only http, https, and data URLs are allowed."

    # Allow data URLs (they're safe as they don't make network requests)
    if parsed.scheme == "data":
        return True, ""

    # Block URLs without hostname
    if not parsed.hostname:
        return False, "URL must have a valid hostname"

    # Block localhost and loopback addresses
    localhost_names = ["localhost", "127.0.0.1", "::1", "0.0.0.0"]
    if parsed.hostname.lower() in localhost_names:
        return False, "Access to localhost is not allowed"

    # Check for private IP addresses
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False, f"Access to private/internal IP addresses is not allowed: {parsed.hostname}"
    except ValueError:
        # Not an IP address, it's a hostname - need to check further
        # Block common internal/metadata endpoints
        blocked_domains = [
            "metadata.google.internal",
            "169.254.169.254",  # AWS/Azure metadata
            "metadata.azure.com",
            "internal",
            ".internal.",
            ".local",
            ".localhost",
        ]
        hostname_lower = parsed.hostname.lower()
        for blocked in blocked_domains:
            if blocked in hostname_lower:
                return False, f"Access to internal domain is not allowed: {parsed.hostname}"

    return True, ""


def ingest_web_url(url: str, artifacts_dir: Path, artifact_id: str, timeout: float = 15.0) -> Dict[str, Any]:
    """Fetch and sanitize a web page.

    Attempts headless rendering via Playwright when available, with graceful
    fallbacks to plain HTTP fetch so smoke tests can run without the optional
    dependency.
    """

    url = url.strip()
    if not url:
        raise ValueError("URL is empty")

    parsed = urlparse(url)
    if not parsed.scheme:
        raise ValueError("URL must include scheme (http/https)")

    # Validate URL to prevent SSRF attacks
    is_safe, error_msg = _is_safe_url(url)
    if not is_safe:
        raise ValueError(f"SSRF protection: {error_msg}")

    warnings: List[str] = []
    html_content = None

    if parsed.scheme == "data":
        try:
            header, payload = url.split(",", 1)
        except ValueError as exc:  # pragma: no cover
            raise ValueError("Invalid data URL") from exc
        if ";base64" in header:
            try:
                html_content = base64.b64decode(payload).decode("utf-8", errors="ignore")
            except Exception as exc:  # pragma: no cover
                warnings.append(f"data url decode failed: {exc}")
                html_content = ""
        else:
            html_content = unquote_to_bytes(payload).decode("utf-8", errors="ignore")
        warnings.append("data URL used; skipping headless fetch")

    try:
        if not html_content:
            html_content = _run_async(_render_with_playwright(url, timeout))
    except Exception as exc:  # pragma: no cover - optional branch
        warnings.append(f"playwright fetch failed: {exc}")

    if not html_content and parsed.scheme in {"http", "https"}:
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url)
                resp.raise_for_status()
                html_content = resp.text
        except Exception as exc:
            warnings.append(f"httpx fetch failed: {exc}")
            html_content = ""

    text, clean_meta = _clean_html(html_content)
    clean_meta.setdefault("title", parsed.netloc or parsed.path)

    web_root = artifacts_dir / "web"
    web_root.mkdir(parents=True, exist_ok=True)
    html_path = web_root / f"{artifact_id}.html"
    text_path = web_root / f"{artifact_id}.txt"
    meta_path = web_root / f"{artifact_id}.metadata.json"

    try:
        html_path.write_text(html_content or "", encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        warnings.append(f"failed to persist html: {exc}")
    try:
        text_path.write_text(text, encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        warnings.append(f"failed to persist text: {exc}")
    try:
        meta_payload = {"url": url, "metadata": clean_meta, "warnings": warnings}
        meta_path.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:  # pragma: no cover
        pass

    return {
        "url": url,
        "text": text,
        "metadata": clean_meta,
        "warnings": warnings,
        "artifacts": {
            "html": str(html_path.relative_to(artifacts_dir)),
            "text": str(text_path.relative_to(artifacts_dir)),
            "meta": str(meta_path.relative_to(artifacts_dir)),
        },
    }

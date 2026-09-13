"""Web capabilities — read API docs and test HTTP endpoints (integration work)."""

import json
import re
from html.parser import HTMLParser

import requests

from bigbro.capabilities.base import Capability


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    return re.sub(r"\s+", " ", " ".join(p.parts)).strip()


class FetchUrl(Capability):
    name = "fetch_url"
    description = (
        "Fetch a web page and return its readable text (HTML stripped). Useful for reading API docs or "
        "references. Returns at most 12k chars."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "max_chars": {"type": "integer", "description": "Default 12000"},
        },
        "required": ["url"],
    }

    def execute(self, url: str, max_chars: int = 12000) -> str:
        max_chars = max(500, min(int(max_chars or 12000), 50000))
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "BigBroAgent/0.1"})
        except requests.RequestException as e:
            return f"ERROR: {e}"
        if "html" in r.headers.get("content-type", ""):
            text = html_to_text(r.text)
        else:
            text = r.text
        return f"HTTP {r.status_code} {url}\n\n{text[:max_chars]}"


class HttpRequest(Capability):
    name = "http_request"
    description = (
        "Send an HTTP request (any method) and return status + body. Use it to test your own APIs or "
        "inspect integration endpoints. json_body and headers must be JSON strings "
        "(e.g. json_body='{\"name\":\"x\"}', headers='{\"Authorization\":\"Bearer ...\"}')."
    )
    parameters = {
        "type": "object",
        "properties": {
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
            "url": {"type": "string"},
            "json_body": {"type": "string", "description": "JSON string body"},
            "headers": {"type": "string", "description": "JSON string of headers"},
        },
        "required": ["method", "url"],
    }

    def execute(self, method: str, url: str, json_body: str = "", headers: str = "") -> str:
        try:
            hdrs = json.loads(headers) if headers else {}
            data = json.loads(json_body) if json_body else None
        except json.JSONDecodeError as e:
            return f"ERROR: headers/json_body must be valid JSON: {e}"
        try:
            r = requests.request(method, url, json=data, headers=hdrs, timeout=30)
        except requests.RequestException as e:
            return f"ERROR: {e}"
        return f"HTTP {r.status_code}\n{r.text[:8000]}"


CAPABILITIES = [FetchUrl, HttpRequest]

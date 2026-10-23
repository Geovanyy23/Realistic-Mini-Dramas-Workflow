"""Scan a package tree for content that must never ship: private media, full
third-party transcripts, frames, signed URLs, secrets."""
from __future__ import annotations

import re
from pathlib import Path

FORBIDDEN_DIRS = {"private", "native-frames", "frames", "recordings", "screenshots", ".state", "runs"}
FORBIDDEN_EXT = {".mp4", ".webm", ".mkv", ".mov", ".srt", ".vtt", ".png", ".jpg", ".jpeg", ".wav", ".mp3", ".pem", ".key"}
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"X-Amz-Signature=|Signature=[A-Za-z0-9%]{20,}|[?&]sig=[A-Za-z0-9%]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
SKIP = {".git", "__pycache__", "node_modules"}


ALLOWED_MEDIA_PREFIXES = ("tests/fixtures", "assets/thumbnail")  # original, owner-made art only


def scan(root: Path, allow_fixture_media_under: str = "tests/fixtures") -> list[str]:
    root = Path(root)
    hits = []
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        parts = set(rel.parts[:-1])
        if parts & SKIP or p.name == Path(__file__).name:
            continue  # the scanner's own pattern table is not a leak
        if parts & FORBIDDEN_DIRS and p.is_file():
            hits.append(f"{rel}: inside a private-only directory")
            continue
        if p.is_file():
            if p.suffix.lower() in FORBIDDEN_EXT and not str(rel).startswith((allow_fixture_media_under,) + ALLOWED_MEDIA_PREFIXES):
                hits.append(f"{rel}: media/secret file extension outside fixtures")
                continue
            if p.suffix.lower() in {".md", ".json", ".py", ".txt", ".yaml", ".yml", ".toml", ".env"}:
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for pat in SECRET_PATTERNS:
                    if pat.search(text):
                        hits.append(f"{rel}: matches secret/signed-URL pattern {pat.pattern[:30]}…")
                        break
    return hits

"""
Agent: link_extractor
----------------------
Fetches a URL and extracts every hyperlink on the page.
Categorises links as: internal (same domain), external, or social media.
Uses only Python stdlib — no external dependencies.

Primary function: link_extractor(url)
"""

import urllib.request
import urllib.parse
from html.parser import HTMLParser

# ── Agent metadata ─────────────────────────────────────────────────────────────

DESCRIPTION = (
    "Fetches a URL and extracts all hyperlinks found on the page. "
    "Returns three categories: internal_links (same domain, useful for discovering sub-pages), "
    "external_links (other websites), and social_links (detected social media profiles). "
    "Use this when you need to discover site structure or find social media accounts."
)

PARAMETERS = {
    "url": {
        "type":        "string",
        "required":    True,
        "description": "Full URL to fetch, must start with http:// or https://",
    }
}

# ── Known social media domains ────────────────────────────────────────────────

_SOCIAL_DOMAINS: dict[str, str] = {
    "linkedin.com":   "LinkedIn",
    "twitter.com":    "Twitter / X",
    "x.com":          "Twitter / X",
    "facebook.com":   "Facebook",
    "instagram.com":  "Instagram",
    "youtube.com":    "YouTube",
    "github.com":     "GitHub",
    "tiktok.com":     "TikTok",
    "pinterest.com":  "Pinterest",
    "reddit.com":     "Reddit",
    "medium.com":     "Medium",
}

# ── HTML link parser ───────────────────────────────────────────────────────────

class _LinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.raw_links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value and not value.startswith(("#", "javascript:", "mailto:", "tel:")):
                    abs_url = urllib.parse.urljoin(self.base_url, value)
                    if abs_url.startswith(("http://", "https://")):
                        # Strip fragment
                        clean = abs_url.split("#")[0].rstrip("/") or abs_url
                        self.raw_links.append(clean)


# ── Primary function ───────────────────────────────────────────────────────────

def link_extractor(url: str) -> dict:
    """
    Fetch `url` and return all hyperlinks categorised by type.

    Args:
        url: Full URL (http:// or https://)

    Returns:
        {
            "url":            str,
            "base_domain":    str,
            "internal_links": list[str],  # same domain
            "external_links": list[str],  # other domains
            "social_links":   list[dict], # [{"platform": "LinkedIn", "url": "..."}]
            "total":          int,
        }
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        html = response.read().decode(charset, errors="replace")

    base_parsed = urllib.parse.urlparse(url)
    base_domain = base_parsed.netloc.lower()

    parser = _LinkParser(url)
    parser.feed(html)

    seen: set[str] = set()
    internal: list[str] = []
    external: list[str] = []
    social:   list[dict] = []

    for link in parser.raw_links:
        if link in seen:
            continue
        seen.add(link)

        parsed_link = urllib.parse.urlparse(link)
        link_domain = parsed_link.netloc.lower()
        bare_domain = link_domain.lstrip("www.")

        # Check social media first
        social_name = next(
            (name for sd, name in _SOCIAL_DOMAINS.items() if sd in bare_domain),
            None,
        )

        if social_name:
            # Deduplicate social links by platform
            if not any(s["platform"] == social_name for s in social):
                social.append({"platform": social_name, "url": link})
        elif link_domain == base_domain or link_domain.endswith("." + base_domain):
            internal.append(link)
        else:
            external.append(link)

    return {
        "url":            url,
        "base_domain":    base_domain,
        "internal_links": sorted(set(internal)),
        "external_links": sorted(set(external)),
        "social_links":   social,
        "total":          len(seen),
    }

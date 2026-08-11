"""Outbound links to The Colony must use the canonical apex.

Why this file exists
--------------------
``thecolony.cc`` and ``thecolony.ai`` both serve the platform, so a ``.cc``
link is not broken and nothing complains about it. But the platform's own
pages declare ``<link rel="canonical" href="https://thecolony.ai/">``, so
every ``.cc`` link we publish points readers and crawlers at the copy the
site itself says is not the canonical one. That is the kind of defect that
survives indefinitely: it 200s.

Two things must NOT be swept up by a blanket search-and-replace, which is
why this is a parsed check with an allowlist rather than a grep:

* ``memory.thecolony.cc`` is **our own hostname** — the value in
  ``docs/CNAME``, and the host GitHub Pages holds the certificate for.
  ``memory.thecolony.ai`` resolves to ``thecolonyai.github.io`` but is not
  claimed as a Pages custom domain, so TLS fails against it with the default
  ``*.github.io`` certificate. Moving the CNAME today takes the site down.
* ``colonist.one@thecolony.cc`` is an **email address**, and ``thecolony.ai``
  publishes no MX record. Moving it silently breaks inbound mail.

So the rule is narrow: a URL whose host is the ``thecolony.cc`` apex, or any
``.thecolony.cc`` subdomain other than our own, is a finding. Hosts we own
and mailto/plain-text addresses are not.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Files we publish. Anything readable here is scanned; a missing file is a
# failure rather than a silent skip, or renaming a file would disable the
# check without anyone noticing.
PUBLISHED = (
    "README.md",
    "skill.md",
    "pyproject.toml",
    "docs/index.html",
    "docs/404.html",
    "docs/skill.md",
    "docs/robots.txt",
    "docs/sitemap.xml",
    "docs/health.json",
)

# Hostnames under thecolony.cc that are ours and cannot move yet. Each needs
# a reason in the module docstring above before it is added here.
OURS = frozenset({"memory.thecolony.cc"})

# Deliberately requires a scheme: `colonist.one@thecolony.cc` is not a URL and
# must not be rewritten. There is a control for exactly that below.
_URL = re.compile(r"https?://([A-Za-z0-9.-]+)")


def _hosts(text: str) -> list[str]:
    return _URL.findall(text)


def _findings(text: str) -> list[str]:
    bad = []
    for host in _hosts(text):
        host = host.rstrip(".").lower()
        if host in OURS:
            continue
        if host == "thecolony.cc" or host.endswith(".thecolony.cc"):
            bad.append(host)
    return bad


def _published_files() -> list[pathlib.Path]:
    return [ROOT / name for name in PUBLISHED]


@pytest.mark.parametrize("path", _published_files(), ids=PUBLISHED)
def test_no_non_canonical_colony_links(path: pathlib.Path) -> None:
    assert path.exists(), f"{path.relative_to(ROOT)} is listed as published but missing"
    found = _findings(path.read_text(encoding="utf-8"))
    assert not found, (
        f"{path.relative_to(ROOT)} links to {sorted(set(found))}; the platform's "
        "own canonical is https://thecolony.ai/ — use that apex for outbound links"
    )


def test_the_scan_is_not_vacuous() -> None:
    """A checker that finds nothing because it read nothing is not a pass.

    Without this, a wrong ROOT or a renamed file makes every case above green
    for the one reason that proves nothing.
    """
    total = sum(len(_hosts(p.read_text(encoding="utf-8"))) for p in _published_files())
    assert total >= 10, f"only {total} URLs seen across {len(PUBLISHED)} files"


def test_the_allowlist_is_actually_exercised() -> None:
    """Our own hostname must really appear, or OURS is dead weight.

    If ``docs/CNAME`` ever moves to .ai, this fails and the allowlist entry —
    and the docstring reason behind it — get revisited rather than lingering.
    """
    seen = {
        h.lower()
        for p in _published_files()
        for h in _hosts(p.read_text(encoding="utf-8"))
    }
    assert OURS & seen, f"{sorted(OURS)} appears nowhere; the allowlist excuses nothing"


def test_control_an_outbound_cc_link_is_caught() -> None:
    """The check must fail on the thing it exists to catch."""
    assert _findings('Built by <a href="https://thecolony.cc">The Colony</a>') == [
        "thecolony.cc"
    ]
    assert _findings("https://forum.thecolony.cc/x") == ["forum.thecolony.cc"]


def test_control_our_own_hostname_is_not_a_finding() -> None:
    assert _findings("https://memory.thecolony.cc/skill.md") == []


def test_control_the_author_email_is_not_a_url() -> None:
    """The one string a blanket .cc rewrite would break, and MX depends on."""
    assert _findings('email = "colonist.one@thecolony.cc"') == []


def test_control_the_canonical_apex_is_not_a_finding() -> None:
    """Otherwise the check would flag the fix as well as the defect."""
    assert _findings("https://thecolony.ai https://memory.thecolony.ai") == []

"""Every URL we publish must point at the canonical host and the current repo.

Why this file exists
--------------------
Both of the defects this guards against **return 200**, which is why neither
would ever be reported:

* ``thecolony.cc`` and ``thecolony.ai`` both serve the platform, but the
  platform's own pages declare ``<link rel="canonical" href="https://thecolony.ai/">``.
  A ``.cc`` link is not broken; it just points at the copy the site disowns.
* ``github.com/TheColonyCC/colony-memory`` **301-redirects** to the new
  ``TheColonyAI`` location for as long as GitHub keeps the rename record --
  and stops working the moment anything else claims that name.

The one string that must never be swept up is ``colonist.one@thecolony.cc``:
it is an **email address**, and ``thecolony.ai`` publishes no MX record, so
rewriting it silently breaks inbound mail. That is why this is a parsed host
check and not a grep -- the regex requires a scheme, and there is a control
asserting the address survives it.

History: this file previously carried an allowlist for ``memory.thecolony.cc``,
our own hostname at the time, plus a guard that would fail if the CNAME ever
moved. On 2026-08-11 it moved, the guard fired, and the allowlist was removed
rather than quietly extended. There are no exemptions left.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Files we publish. A missing file is a failure rather than a silent skip, or
# renaming one would disable the check without anyone noticing.
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

SITE_HOST = "memory.thecolony.ai"
REPO_URL = "github.com/TheColonyAI/colony-memory"
STALE_REPO_URL = "github.com/TheColonyCC/colony-memory"

# Deliberately requires a scheme: `colonist.one@thecolony.cc` is not a URL and
# must not be rewritten. There is a control for exactly that below.
_URL = re.compile(r"https?://([A-Za-z0-9.-]+)")


def _hosts(text: str) -> list[str]:
    return [h.rstrip(".").lower() for h in _URL.findall(text)]


def _findings(text: str) -> list[str]:
    return [h for h in _hosts(text) if h == "thecolony.cc" or h.endswith(".thecolony.cc")]


def _published_files() -> list[pathlib.Path]:
    return [ROOT / name for name in PUBLISHED]


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", _published_files(), ids=PUBLISHED)
def test_no_non_canonical_colony_host(path: pathlib.Path) -> None:
    assert path.exists(), f"{path.relative_to(ROOT)} is listed as published but missing"
    found = _findings(_read(path))
    assert not found, (
        f"{path.relative_to(ROOT)} links to {sorted(set(found))}; the platform's "
        f"own canonical is https://thecolony.ai/ and this site is https://{SITE_HOST}/"
    )


@pytest.mark.parametrize("path", _published_files(), ids=PUBLISHED)
def test_no_stale_repository_url(path: pathlib.Path) -> None:
    """A 301 is not a reason to keep a wrong URL -- it is why nobody notices."""
    assert STALE_REPO_URL not in _read(path), (
        f"{path.relative_to(ROOT)} still points at {STALE_REPO_URL}; the repo moved "
        f"to {REPO_URL} and the old path only works while GitHub keeps the rename "
        "record"
    )


def test_cname_is_the_host_we_claim_to_be() -> None:
    """docs/CNAME decides the domain; every other file merely describes it."""
    cname = (ROOT / "docs" / "CNAME").read_text(encoding="utf-8").strip()
    assert cname == SITE_HOST, f"docs/CNAME is {cname!r}, the docs say {SITE_HOST!r}"


def test_the_scan_is_not_vacuous() -> None:
    """A checker that finds nothing because it read nothing is not a pass.

    Without this, a wrong ROOT or a renamed file makes every case above green
    for the one reason that proves nothing.
    """
    total = sum(len(_hosts(_read(p))) for p in _published_files())
    assert total >= 10, f"only {total} URLs seen across {len(PUBLISHED)} files"


def test_the_site_host_and_repo_are_actually_present() -> None:
    """The checks above only forbid. Something has to require the right values.

    Otherwise deleting every URL in the repo would pass the whole file.
    """
    blob = "".join(_read(p) for p in _published_files())
    assert SITE_HOST in blob, f"{SITE_HOST} appears nowhere in the published files"
    assert REPO_URL in blob, f"{REPO_URL} appears nowhere in the published files"


def test_control_a_cc_url_is_caught() -> None:
    """The check must fail on the thing it exists to catch."""
    assert _findings('Built by <a href="https://thecolony.cc">The Colony</a>') == [
        "thecolony.cc"
    ]
    assert _findings("https://memory.thecolony.cc/skill.md") == ["memory.thecolony.cc"]


def test_control_the_author_email_is_not_a_url() -> None:
    """The one string a blanket .cc rewrite would break, and MX depends on."""
    assert _findings('email = "colonist.one@thecolony.cc"') == []


def test_control_the_canonical_apex_is_not_a_finding() -> None:
    """Otherwise the check would condemn the fix as well as the defect."""
    assert _findings(f"https://thecolony.ai https://{SITE_HOST}/skill.md") == []


def test_control_the_orgs_other_repos_are_not_flagged() -> None:
    """Only *this* repo moved; links to TheColonyCC's other repos stay correct."""
    assert STALE_REPO_URL not in "https://github.com/TheColonyCC/colony-sdk-conformance"

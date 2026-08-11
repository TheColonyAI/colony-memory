"""The real colony-sdk must still satisfy the slice we depend on.

Why this file exists
--------------------
Every other test in this suite runs against ``FakeVault`` in conftest. That fake
is hand-written and faithful, which is better than a ``MagicMock`` — but it is
still *our* object implementing *our* Protocol. Nothing anywhere asserted that
``colony_sdk.ColonyClient`` implements it too.

So the suite was green in a way causally disconnected from the dependency it
runs on. If the SDK renamed ``vault_upload_file`` tomorrow, all twenty tests
would still pass and ``pip install colony-memory`` would ship a package that
raises ``AttributeError`` on first backup — at the exact moment an agent is
restoring memory after a crash.

The dependency is declared as a floor (``colony-sdk>=1.20``), so a new SDK
release changes what we resolve to with **no commit here to trigger a build**.
That is why this test is paired with a scheduled CI run: a push-triggered suite
cannot observe a failure that arrives without a push.

Reflection over an instance would need credentials, so these assert against the
class. Presence catches removal and rename; the signature check additionally
catches a parameter rename, which presence alone cannot see.
"""

from __future__ import annotations

import inspect

import pytest

from colony_memory.client import VaultBackend

# name -> the positional parameters we actually pass (excluding self)
REQUIRED = {
    "vault_status": (),
    "vault_list_files": (),
    "vault_get_file": ("filename",),
    "vault_upload_file": ("filename", "content"),
    "vault_delete_file": ("filename",),
}


@pytest.fixture(scope="module")
def sdk_client_cls():
    colony_sdk = pytest.importorskip("colony_sdk")
    return colony_sdk.ColonyClient


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_sdk_still_exposes_the_method(sdk_client_cls, name):
    assert hasattr(sdk_client_cls, name), (
        f"colony_sdk.ColonyClient no longer has {name!r}. Colony Memory calls it "
        f"directly; installs would fail on first use."
    )
    assert callable(getattr(sdk_client_cls, name))


@pytest.mark.parametrize("name,params", sorted(REQUIRED.items()))
def test_sdk_method_still_accepts_our_arguments(sdk_client_cls, name, params):
    """We call these by keyword, so a renamed parameter breaks us silently."""
    sig = inspect.signature(getattr(sdk_client_cls, name))
    accepted = [p for p in sig.parameters if p != "self"]
    missing = [p for p in params if p not in accepted]
    assert not missing, (
        f"colony_sdk.ColonyClient.{name}{sig} no longer accepts {missing}; "
        f"Colony Memory passes {list(params)}."
    )


def test_sdk_class_structurally_satisfies_vault_backend(sdk_client_cls):
    missing = [n for n in REQUIRED if not hasattr(sdk_client_cls, n)]
    assert not missing, f"VaultBackend slice missing from the SDK: {missing}"


# --- controls -------------------------------------------------------------
# Without these, the three tests above are satisfied by any object at all and
# a green run would certify nothing.

class _Incomplete:
    """Implements the protocol except for one method."""

    def vault_status(self) -> dict: ...
    def vault_list_files(self) -> dict: ...
    def vault_get_file(self, filename: str) -> dict: ...
    def vault_upload_file(self, filename: str, content: str) -> dict: ...
    # vault_delete_file deliberately absent


class _WrongParamName:
    def vault_status(self) -> dict: ...
    def vault_list_files(self) -> dict: ...
    def vault_get_file(self, path: str) -> dict: ...          # was `filename`
    def vault_upload_file(self, filename: str, content: str) -> dict: ...
    def vault_delete_file(self, filename: str) -> dict: ...


def test_control_missing_method_is_detected():
    missing = [n for n in REQUIRED if not hasattr(_Incomplete, n)]
    assert missing == ["vault_delete_file"], (
        "the presence check cannot see a missing method — it certifies nothing"
    )
    assert not isinstance(_Incomplete(), VaultBackend)


def test_control_renamed_parameter_is_detected():
    sig = inspect.signature(_WrongParamName.vault_get_file)
    accepted = [p for p in sig.parameters if p != "self"]
    assert "filename" not in accepted, (
        "the signature check cannot see a renamed parameter — presence alone "
        "would have passed this object"
    )
    # ...and note the presence check alone WOULD have passed it, which is the
    # whole reason the signature test exists next to it.
    assert all(hasattr(_WrongParamName, n) for n in REQUIRED)


def test_control_the_fake_satisfies_the_same_protocol(vault):
    """If the fake did not satisfy it either, the protocol would be untested."""
    assert isinstance(vault, VaultBackend)

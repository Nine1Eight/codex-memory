from __future__ import annotations

import pytest

from packages.domain import (
    AuthorityDecision,
    Claim,
    Coverage,
    DeduplicationKeyInput,
    LocalSigner,
    ViewClass,
    canonical_json,
    compute_claim_merkle_root,
    compute_deduplication_key,
    compute_viewing_confidence,
    qualify_view,
)


def test_canonical_json_orders_keys() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_deduplication_key_is_stable() -> None:
    value = DeduplicationKeyInput("a", "b", "c", "d", "e")
    assert compute_deduplication_key(value) == compute_deduplication_key(value)


def test_merkle_root_changes_on_single_byte_mutation() -> None:
    claims = [
        Claim("c1", "alpha", 2, "asserted", ("e1",), 1.0, 0.0, 0.9),
        Claim("c2", "beta", 3, "asserted", ("e2",), 1.0, 0.0, 0.8),
    ]
    root = compute_claim_merkle_root(claims)
    mutated = [
        Claim("c1", "alpha", 2, "asserted", ("e1",), 1.0, 0.0, 0.9),
        Claim("c2", "betb", 3, "asserted", ("e2",), 1.0, 0.0, 0.8),
    ]
    assert root != compute_claim_merkle_root(mutated)


def test_viewing_confidence_matches_formula() -> None:
    assert compute_viewing_confidence(Coverage(1, 1, 1, 1), 1, 1, 1, 1) == 100.0


def test_qualify_view_requires_thresholds() -> None:
    qualified, vcs = qualify_view(
        ViewClass.MULTIMODAL,
        AuthorityDecision.ALLOW,
        Coverage(required=0.9),
        0.95,
        0.8,
        0.91,
        1,
        False,
        (),
    )
    assert qualified is True
    assert vcs >= 82


def test_local_signer_verifies_payload() -> None:
    signer = LocalSigner("kid", b"secret")
    payload = {"hello": "world"}
    signature = signer.sign(payload)
    assert signer.verify(payload, signature)
    assert not signer.verify({"hello": "changed"}, signature)

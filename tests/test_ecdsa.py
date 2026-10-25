#!/usr/bin/env python3
"""
Test vector for Z0SignatureScheme v1.0.0 (secp256k1 + RFC 6979 + SHA-256).

Vector source: RFC 6979 §A.2.5 (secp256k1, SHA-256, message "sample").

Run:
    python tests/test_ecdsa.py
Exit code 0 = pass, 1 = fail.
"""
import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from sign import _mul, _rfc6979_k, N, G  # noqa: E402

# --- RFC 6979 §A.2.5 known-answer -------------------------------------------
D  = 0xC9AFA9D845BA75166B5C215767B1D6934E50C3DB36E89B127B8A622B120F6721
MSG = b"sample"
HASH = hashlib.sha256(MSG).digest()
E   = int.from_bytes(HASH, "big") % N

# Expected k (RFC 6979 §A.2.5 for SHA-256, message "sample")
K_EXPECTED = 0xA6E3C57DD01ABE90086538398355DD4C3B17AA873382B0F24D6129493D8AAD60

# Expected R, S for the above (RFC 6979 §A.2.5)
R_EXPECTED = 0xEFD48B2AACB6A8FD1140DD9CD45E81D69D2C877B56AAF991C34D0EA84EAF3716
S_EXPECTED = 0xF7CB1C942D657C41D436C7A1B6E29F65F3E900DBB9AFF4064DC4AB2F843ACDA8

def test_rfc6979_k():
    k = _rfc6979_k(D, HASH)
    assert k == K_EXPECTED, f"k mismatch:\n  got {k:064x}\n  exp {K_EXPECTED:064x}"

def test_signature():
    k = _rfc6979_k(D, HASH)
    Kp = _mul(k, G)
    assert Kp is not None
    R = Kp[0] % N
    S = (pow(k, N - 2, N) * (E + D * R)) % N
    assert R == R_EXPECTED, f"R mismatch:\n  got {R:064x}\n  exp {R_EXPECTED:064x}"
    assert S == S_EXPECTED, f"S mismatch:\n  got {S:064x}\n  exp {S_EXPECTED:064x}"

def test_verify_roundtrip():
    from verify import ecdsa_verify, _mul as _mul_v  # same curve
    Q = _mul_v(D, G)
    k = _rfc6979_k(D, HASH)
    Kp = _mul(k, G)
    R = Kp[0] % N
    S = (pow(k, N - 2, N) * (E + D * R)) % N
    assert ecdsa_verify(Q, R, S, MSG), "verify rejected a valid signature"
    assert not ecdsa_verify(Q, R, S, b"tampered"), "verify accepted a bad message"

if __name__ == "__main__":
    failures = 0
    for name, fn in [("rfc6979_k", test_rfc6979_k),
                     ("signature",  test_signature),
                     ("verify",     test_verify_roundtrip)]:
        try:
            fn()
            print(f"[✓] {name}")
        except AssertionError as e:
            print(f"[✗] {name}: {e}")
            failures += 1
    sys.exit(0 if failures == 0 else 1)

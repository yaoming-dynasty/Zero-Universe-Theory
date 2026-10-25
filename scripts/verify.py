#!/usr/bin/env python3
"""
Z0SignatureScheme v1.0.0 — verifier.

Parses a Z0 header from a markdown file and verifies the ECDSA/SHA-256
signature against the embedded public key.

Usage:
    python scripts/verify.py docs/axioms.md
Exit codes:
    0 = VALID
    1 = INVALID
    2 = malformed header / missing fields
"""
import hashlib
import pathlib
import re
import sys

# --- secp256k1 (same constants as sign.py) ----------------------------------
P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
A  = 0
N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (GX, GY)

def _add(P1, P2):
    if P1 is None: return P2
    if P2 is None: return P1
    x1, y1 = P1; x2, y2 = P2
    if x1 == x2 and (y1 + y2) % P == 0: return None
    if x1 == x2 and y1 == y2:
        lam = ((3 * x1 * x1 + A) * pow(2 * y1, P - 2, P)) % P
    else:
        lam = ((y2 - y1) * pow(x2 - x1, P - 2, P)) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)

def _mul(k, Pt):
    k %= N
    if k == 0 or Pt is None: return None
    R = None; Q = Pt
    while k:
        if k & 1: R = _add(R, Q)
        Q = _add(Q, Q); k >>= 1
    return R

# --- header parsing ----------------------------------------------------------
def parse_header(text: str):
    """Return (fields: dict, body: bytes) or raise ValueError."""
    if not text.startswith("---\n"):
        raise ValueError("file does not start with a Z0 header")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        raise ValueError("header has no closing '---'")
    header = rest[:end]
    body = rest[end + len("\n---\n"):].encode("utf-8")
    fields = {}
    for line in header.splitlines():
        m = re.match(r"^([A-Z_]+):\s*(.+)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields, body

def parse_pk(hexstr: str):
    h = hexstr.removeprefix("0x")
    if len(h) != 128: raise ValueError("public key must be 128 hex chars (uncompressed point)")
    return (int(h[:64], 16), int(h[64:], 16))

def parse_sig(fields):
    R = int(fields["R"].removeprefix("0x"), 16)
    S = int(fields["S"].removeprefix("0x"), 16)
    return R, S

def ecdsa_verify(Q, R, S, body: bytes) -> bool:
    if not (1 <= R < N and 1 <= S < N): return False
    e = int.from_bytes(hashlib.sha256(body).digest(), "big") % N
    w  = pow(S, N - 2, N)
    u1 = (e * w) % N
    u2 = (R * w) % N
    X  = _add(_mul(u1, G), _mul(u2, Q))
    if X is None: return False
    return (X[0] % N) == R

def main(path: str) -> int:
    text = pathlib.Path(path).read_text(encoding="utf-8")
    try:
        fields, body = parse_header(text)
        Q = parse_pk(fields["PUBLIC_IDENTITY_KEY (OUTSIDE_BOUNDARY) — secp256k1, uncompressed"]
                     if "PUBLIC_IDENTITY_KEY (OUTSIDE_BOUNDARY) — secp256k1, uncompressed" in fields
                     else fields.get("PUBLIC_IDENTITY_KEY", ""))
        R, S = parse_sig(fields)
    except (KeyError, ValueError) as e:
        print(f"MALFORMED: {e}")
        return 2

    # Fast integrity pre-check: body hash must match before doing curve math.
    expected = fields.get("BODY_SHA256")
    actual   = hashlib.sha256(body).hexdigest()
    if expected and expected != actual:
        print(f"INVALID: body hash mismatch (expected {expected[:16]}…, got {actual[:16]}…)")
        return 1

    ok = ecdsa_verify(Q, R, S, body)
    print("VALID" if ok else "INVALID")
    return 0 if ok else 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python verify.py <file.md>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))

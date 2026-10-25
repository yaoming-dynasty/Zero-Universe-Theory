#!/usr/bin/env python3
"""
Z0SignatureScheme v1.0.0 — signer.

Implements ECDSA over secp256k1 with deterministic nonces (RFC 6979).
Persists the private scalar to ~/.z0/private.key on first run; loads it
on every subsequent run so the public key (Q = d·G) is stable.

Usage:
    python scripts/sign.py                 # sign all *.md under docs/
    python scripts/sign.py docs/axioms.md  # sign one file
    python scripts/sign.py --all           # sign every non-excluded *.md
"""
import hashlib
import hmac
import os
import pathlib
import sys

# --- secp256k1 ---------------------------------------------------------------
P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
A  = 0
B  = 7
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G  = (GX, GY)

# --- curve arithmetic --------------------------------------------------------
def _add(P1, P2):
    if P1 is None: return P2
    if P2 is None: return P1
    x1, y1 = P1; x2, y2 = P2
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
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
        Q = _add(Q, Q)
        k >>= 1
    return R

# --- RFC 6979 deterministic k -----------------------------------------------
def _rfc6979_k(d: int, h: bytes) -> int:
    """Return a deterministic nonce k in [1, N-1] per RFC 6979 §3.2 (HMAC-SHA256)."""
    x = d.to_bytes(32, "big")
    # bits2octets(h): reduce h modulo N, output 32 bytes
    h_int = int.from_bytes(h, "big") % N
    h1 = h_int.to_bytes(32, "big")
    V = b"\x01" * 32
    K = b"\x00" * 32
    K = hmac.new(K, V + b"\x00" + x + h1, hashlib.sha256).digest()
    V = hmac.new(K, V, hashlib.sha256).digest()
    K = hmac.new(K, V + b"\x01" + x + h1, hashlib.sha256).digest()
    V = hmac.new(K, V, hashlib.sha256).digest()
    while True:
        V = hmac.new(K, V, hashlib.sha256).digest()
        k = int.from_bytes(V, "big")
        if 1 <= k < N:
            return k
        K = hmac.new(K, V + b"\x00", hashlib.sha256).digest()
        V = hmac.new(K, V, hashlib.sha256).digest()

# --- key management ----------------------------------------------------------
KEY_PATH = pathlib.Path.home() / ".z0" / "private.key"

def load_or_create_key() -> int:
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        hexd = KEY_PATH.read_text().strip()
        return int(hexd, 16)
    d = int.from_bytes(os.urandom(32), "big") % (N - 1) + 1
    KEY_PATH.write_text(f"{d:064x}\n")
    os.chmod(KEY_PATH, 0o600)
    print(f"[*] New private key written to {KEY_PATH} (mode 600). Back it up.")
    return d

def public_key(d: int) -> tuple:
    Q = _mul(d, G)
    if Q is None: raise RuntimeError("invalid private key")
    return Q

# --- signing -----------------------------------------------------------------
def sign(body: bytes, d: int) -> tuple:
    """Return (R, S) as integers for SHA-256(body)."""
    h = hashlib.sha256(body).digest()
    e = int.from_bytes(h, "big") % N
    while True:
        k = _rfc6979_k(d, h)
        Kp = _mul(k, G)
        if Kp is None: continue
        R = Kp[0] % N
        if R == 0: continue
        S = (pow(k, N - 2, N) * (e + d * R)) % N
        if S == 0: continue
        return R, S

# --- header parsing / rewriting ---------------------------------------------
OPEN  = "---\n"
CLOSE = "---\n"

def split_header(text: str) -> bytes:
    """Return the body bytes (everything after the closing '---' of the
    header, or the whole file if no header is present)."""
    if not text.startswith(OPEN):
        return text.encode("utf-8")
    rest = text[len(OPEN):]
    idx = rest.find("\n" + CLOSE)
    if idx == -1:
        return text.encode("utf-8")
    return rest[idx + 1 + len(CLOSE):].encode("utf-8")

def make_header(body: bytes, d: int) -> str:
    Q = public_key(d)
    pk_hex = f"0x{Q[0]:064X}{Q[1]:064X}"
    R, S = sign(body, d)
    body_hash = hashlib.sha256(body).hexdigest()
    return (
        "---\n"
        "METADATA & CRYPTOGRAPHIC IDENTITY\n"
        "Author:       Christopher Thomas Ronio\n"
        "Framework:    Zero-Universe Theory (Z0)\n"
        "Core Anchor:  ⟨Inside⟩ + ⟨Outside⟩ − ⟨Scale⟩ = 0   (conceptual)\n"
        "Timestamp:    2026-10-24 14:55:00 UTC\n"
        "-----------------------------------------------------------------\n"
        "PUBLIC IDENTITY KEY (OUTSIDE_BOUNDARY) — secp256k1, uncompressed\n"
        f"{pk_hex}\n"
        "-----------------------------------------------------------------\n"
        "DOCUMENT DIGITAL SIGNATURE (R, S) — ECDSA/SHA-256, RFC 6979 nonce\n"
        f"R: 0x{R:064x}\n"
        f"S: 0x{S:064x}\n"
        f"BODY_SHA256: {body_hash}\n"
        "-----------------------------------------------------------------\n"
        "LEGAL STATUS & LICENSE\n"
        "Copyright (c) 2026 Christopher Thomas Ronio. All Rights Reserved.\n"
        "Licensed under the Creative Commons Attribution 4.0 International (CC BY 4.0).\n"
        "Verification Protocol: Z0SignatureScheme v1.0.0\n"
        "---\n\n"
    )

def rewrite(path: pathlib.Path, d: int) -> None:
    text = path.read_text(encoding="utf-8")
    body = split_header(text)
    header = make_header(body, d)
    path.write_text(header + body.decode("utf-8"), encoding="utf-8")
    print(f"[✓] signed {path}")

EXCLUDE = {"readme.md", "license.md", "index.md"}

def main(argv: list) -> int:
    d = load_or_create_key()
    targets: list = []
    if len(argv) > 1 and argv[1] not in ("--all",):
        targets = [pathlib.Path(argv[1])]
    elif len(argv) > 1 and argv[1] == "--all":
        targets = [p for p in pathlib.Path(".").rglob("*.md")
                   if p.name.lower() not in EXCLUDE
                   and not any(part.startswith(".") for part in p.parts)]
    else:
        targets = [p for p in pathlib.Path("docs").rglob("*.md")]
    for p in targets:
        if not p.exists():
            print(f"[!] missing {p}", file=sys.stderr)
            return 2
        rewrite(p, d)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

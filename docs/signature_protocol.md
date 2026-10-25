# Z0SignatureScheme v1.0.0

**Status:** implemented. Verifier: `scripts/verify.py`. Signer: `scripts/sign.py`.
**Note:** this scheme is cryptographic (ECDSA over secp256k1). It is distinct
from the *symbolic seal* in `docs/INDEX.md`, which is conceptual and does not
certify anything.

## 1. Curve

secp256k1, as defined in SEC 2 v2. Parameters:

    p  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    a  = 0
    b  = 7
    Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
    Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
    n  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

## 2. Keys

- **Private key:** an integer `d` in `[1, n-1]`, persisted at `~/.z0/private.key`
  (mode 600, never committed).
- **Public key:** the curve point `Q = d·G`, written in uncompressed form:
  `0x` followed by 128 hex characters = `Q.x` (32 bytes) || `Q.y` (32 bytes).

The public key is **stable** across runs of the signer. It is not a constant.

## 3. Canonical message

The signed message is:

    body = UTF-8 bytes of the document after the closing '---' of the header

The body is **not** normalized (no whitespace stripping, no line-ending
conversion). If a repository stores files with CRLF, the signer and verifier
must both read CRLF; if LF, both must read LF. Pick LF for this repo (see
`.gitattributes`).

## 4. Signature equation

Standard ECDSA over SHA-256, with deterministic nonce per RFC 6979:

    h  = SHA256(body)                       (32 bytes)
    e  = int(h) mod n
    k  = RFC6979_k(d, h)                    (HMAC-SHA256, 32-byte output)
    K  = k·G
    R  = K.x mod n
    S  = k⁻¹ · (e + d·R) mod n

`(R, S)` are written as 32-byte big-endian hex in the header.

## 5. Verification

Given `(Q, R, S, body)`:

    e  = int(SHA256(body)) mod n
    w  = S⁻¹ mod n
    u1 = e·w mod n
    u2 = R·w mod n
    X  = u1·G + u2·Q
    accept iff X ≠ O and (X.x mod n) = R

Reject if `R` or `S` is outside `[1, n-1]`, or if `BODY_SHA256` in the header
does not equal `SHA256(body)`.

## 6. Header format

    ---
    METADATA & CRYPTOGRAPHIC IDENTITY
    Author:       Christopher Thomas Ronio
    Framework:    Zero-Universe Theory (Z0)
    Core Anchor:  ⟨Inside⟩ + ⟨Outside⟩ − ⟨Scale⟩ = 0   (conceptual)
    Timestamp:    2026-10-24 14:55:00 UTC
    -----------------------------------------------------------------
    PUBLIC IDENTITY KEY (OUTSIDE_BOUNDARY) — secp256k1, uncompressed
    0x<128 hex chars>
    -----------------------------------------------------------------
    DOCUMENT DIGITAL SIGNATURE (R, S) — ECDSA/SHA-256, RFC 6979 nonce
    R: 0x<64 hex chars>
    S: 0x<64 hex chars>
    BODY_SHA256: <64 hex chars>
    -----------------------------------------------------------------
    LEGAL STATUS & LICENSE
    Copyright (c) 2026 Christopher Thomas Ronio. All Rights Reserved.
    Licensed under the Creative Commons Attribution 4.0 International (CC BY 4.0).
    Verification Protocol: Z0SignatureScheme v1.0.0
    ---

    <body — signed verbatim>

The header is separated from the body by exactly one blank line after the
closing `---`. Anything before the first `---` is ignored; the signature covers
**only** the body.

## 7. Threat model

- **Prevents:** accidental or malicious modification of a signed document
  without detection (an attacker who changes the body cannot produce a valid
  `(R, S)` without the private key).
- **Does not prevent:** an attacker with write access to `~/.z0/private.key`.
  Back that file up; treat it as the root of trust.
- **Does not prevent:** re-signing with a *different* private key. The verifier
  trusts the public key embedded in the header; there is no external PKI.
  Distribution of the trusted public key is out of scope for v1.0.0.

## 8. Test vector

`tests/test_ecdsa.py` contains a known-good RFC 6979 secp256k1 vector.
Running it proves the implementation matches the spec.

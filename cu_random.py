"""
cu_random.py
------------

A Python random number generator backed by the University of Colorado Boulder
Randomness Beacon (CURBy) HTTP API.

API docs: https://random.colorado.edu/api
Base path: https://random.colorado.edu/api

The beacon publishes signed pulses. Each pulse payload contains 256 bits of
public randomness in ``payload.randomness`` (a 64-character hex string). This
module fetches the latest pulse and uses that randomness as the entropy source.

Endpoint used:
    GET /chains/{chainCid}/pulses/latest   -> most recent pulse on a chain

Notes
-----
* The response format is DAG-JSON, which is a subset of plain JSON, so the
  standard ``json`` module parses it fine.
* The beacon recommends verifying responses against its protocol using the
  official client library when the randomness is used for security-sensitive
  purposes. This module fetches and consumes the raw ``randomness`` value;
  signature verification is intentionally left to the caller (see the
  ``Pulse.signature`` / ``Pulse.previous_signature`` fields).
* Only the Python standard library is used (no ``requests`` dependency).

Example
-------
    from cu_random import CURandom, randint, random, choice, randbytes, refresh

    rng = CURandom()                                   # fetch latest beacon pulse
    print(rng.random())                                # float in [0.0, 1.0)
    print(rng.randint(1, 100))                         # int in [1, 100]
    print(rng.choice(["heads", "tails"]))
    print(rng.randbytes(16).hex())                     # 16 random bytes

    refresh()                                          # pull a fresh pulse from the beacon
    print(rng.randint(1, 6))                           # roll a die with new beacon entropy
"""

from __future__ import annotations

import json
import random as _stdlib_random
import secrets
from dataclasses import dataclass
from typing import Any, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://random.colorado.edu/api"
DEFAULT_CHAIN_CID = (
    "bafyriqa5k2d3t3r774geicueaed2wc2fosjwqeexfhwbptfgq7rcn5mwucnhfeuxu2nxbrch3rl6yqjlozhuswo5ln3xwjm35iftt3tpqlcgs"
)

REQUEST_TIMEOUT = 10.0  # seconds


@dataclass
class Pulse:
    """A single parsed beacon pulse."""

    cid: str                 # CID of the pulse object itself
    chain: str               # CID of the chain this pulse belongs to
    index: int               # numeric index of the pulse on the chain
    round: int               # beacon round number
    randomness_hex: str      # 64-char hex string (256 bits of randomness)
    previous_signature: str  # signature of the previous round
    signature: str           # signature of this round
    source: str              # e.g. "random.colorado.edu"


class CURandom:
    """Random generator that draws entropy from CU Boulder's Randomness Beacon.

    Each beacon pulse contributes 32 bytes (256 bits). Those bytes are buffered
    and handed out on demand. When the buffer is exhausted, the next pulse is
    fetched automatically (``refresh()``), so output chains across beacon
    rounds.

    Parameters
    ----------
    chain_cid:
        CID of the beacon chain to read from.
    base_url:
        API base path.
    fallback:
        If True and the beacon is unreachable, fall back to Python's
        ``secrets`` module so calls never block/fail. If False, beacon errors
        are propagated.
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        chain_cid: str = DEFAULT_CHAIN_CID,
        base_url: str = DEFAULT_BASE_URL,
        *,
        fallback: bool = True,
        timeout: float = REQUEST_TIMEOUT,
    ) -> None:
        self.chain_cid = chain_cid
        self.base_url = base_url.rstrip("/")
        self.fallback = fallback
        self.timeout = timeout

        # Local PRNG seeded from the beacon (convenience for gauss(), etc.)
        self._rng = _stdlib_random.Random()

        # Buffer of raw beacon bytes yet to be handed out
        self._buffer: bytearray = bytearray()
        self._position: int = 0

        self._last_pulse: Optional[Pulse] = None
        self.refresh()

    # ------------------------------------------------------------------ #
    # Beacon I/O
    # ------------------------------------------------------------------ #
    def fetch_latest_pulse(self) -> Pulse:
        """Fetch and parse the latest pulse from the beacon."""
        url = f"{self.base_url}/chains/{self.chain_cid}/pulses/latest"
        req = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "cu-random-generator/1.0",
            },
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                if resp.status >= 400:
                    raise RuntimeError(f"HTTP {resp.status}: {body}")
                data = json.loads(body)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not reach beacon API: {exc}") from exc

        content = data["data"]["content"]
        payload = content["payload"]

        return Pulse(
            cid=data["cid"]["/"],
            chain=content["chain"]["/"],
            index=content["index"],
            round=payload["round"],
            randomness_hex=payload["randomness"],
            previous_signature=payload["previous_signature"],
            signature=payload["signature"],
            source=content.get("source", ""),
        )

    def refresh(self) -> Pulse:
        """Pull a fresh pulse from the beacon and re-seed from its randomness.

        Returns the fetched :class:`Pulse`. On beacon failure, keeps the old
        buffer (or uses ``secrets`` if ``fallback`` is True) and re-raises
        unless fallback is enabled.
        """
        try:
            pulse = self.fetch_latest_pulse()
        except Exception:
            if self.fallback:
                # Keep going with CSPRNG bytes so the generator stays usable.
                self._buffer = bytearray(secrets.token_bytes(32))
                self._position = 0
                self._rng.seed(secrets.token_bytes(32))
                if self._last_pulse is not None:
                    return self._last_pulse
                raise
            raise

        self._last_pulse = pulse
        seed_bytes = bytes.fromhex(pulse.randomness_hex)
        self._buffer = bytearray(seed_bytes)
        self._position = 0
        self._rng.seed(seed_bytes)
        return pulse

    # ------------------------------------------------------------------ #
    # Entropy stream
    # ------------------------------------------------------------------ #
    def _draw(self, n: int) -> bytes:
        """Draw ``n`` random bytes from the beacon buffer, refilling as needed."""
        out = bytearray()
        remaining = n
        while remaining > 0:
            if self._position >= len(self._buffer):
                try:
                    self.refresh()
                except Exception:
                    if self.fallback:
                        out.extend(secrets.token_bytes(remaining))
                        return bytes(out)
                    raise
            avail = len(self._buffer) - self._position
            take = min(avail, remaining)
            out.extend(self._buffer[self._position : self._position + take])
            self._position += take
            remaining -= take
        return bytes(out)

    # ------------------------------------------------------------------ #
    # random-like API
    # ------------------------------------------------------------------ #
    def randbytes(self, n: int) -> bytes:
        """Return ``n`` random bytes from the beacon."""
        if n < 0:
            raise ValueError("n must be non-negative")
        return self._draw(n)

    def random(self) -> float:
        """Random float in [0.0, 1.0)."""
        return int.from_bytes(self._draw(8), "big") / 2**64

    def randint(self, a: int, b: int) -> int:
        """Random integer N such that a <= N <= b (uniform, rejection sampled)."""
        if a > b:
            raise ValueError("a must be <= b")
        span = b - a
        bits = span.bit_length() + 1  # headroom keeps rejection sampling rare
        byte_len = (bits + 7) // 8
        mask = (1 << bits) - 1
        while True:
            value = int.from_bytes(self._draw(byte_len), "big") & mask
            if value <= span:
                return a + value

    def randbelow(self, n: int) -> int:
        """Random integer in [0, n)."""
        if n <= 0:
            raise ValueError("n must be positive")
        return self.randint(0, n - 1)

    def choice(self, seq: Sequence[Any]) -> Any:
        """Choose a random element from a non-empty sequence."""
        if not seq:
            raise IndexError("cannot choose from an empty sequence")
        return seq[self.randbelow(len(seq))]

    def shuffle(self, seq: list) -> None:
        """Shuffle a list in place using beacon entropy (Fisher-Yates)."""
        for i in range(len(seq) - 1, 0, -1):
            j = self.randint(0, i)
            seq[i], seq[j] = seq[j], seq[i]

    def uniform(self, a: float, b: float) -> float:
        """Random float in [a, b)."""
        return a + (b - a) * self.random()

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Gaussian draw (uses the beacon-seeded stdlib RNG)."""
        return self._rng.gauss(mu, sigma)

    def seed_from_beacon(self) -> int:
        """Re-seed everything from a fresh beacon pulse; returns the round used."""
        return self.refresh().round

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #
    @property
    def last_pulse(self) -> Optional[Pulse]:
        """The most recently fetched pulse, or None if never refreshed."""
        return self._last_pulse


# --------------------------------------------------------------------- #
# Module-level convenience instance (import and use directly)
# --------------------------------------------------------------------- #
_default = CURandom()


def refresh() -> Pulse:
    """Fetch a new beacon pulse and re-seed the default generator."""
    return _default.refresh()


def random() -> float:
    return _default.random()


def randint(a: int, b: int) -> int:
    return _default.randint(a, b)


def randbelow(n: int) -> int:
    return _default.randbelow(n)


def choice(seq: Sequence[Any]) -> Any:
    return _default.choice(seq)


def shuffle(seq: list) -> None:
    _default.shuffle(seq)


def randbytes(n: int) -> bytes:
    return _default.randbytes(n)


def uniform(a: float, b: float) -> float:
    return _default.uniform(a, b)


def gauss(mu: float = 0.0, sigma: float = 1.0) -> float:
    return _default.gauss(mu, sigma)


def last_pulse() -> Optional[Pulse]:
    return _default.last_pulse


# --------------------------------------------------------------------- #
# CLI demo
# --------------------------------------------------------------------- #
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CU Boulder Randomness Beacon random-generator demo"
    )
    parser.add_argument(
        "--chain-cid",
        default=DEFAULT_CHAIN_CID,
        help="beacon chain CID (default: latest known chain)",
    )
    parser.add_argument(
        "--int",
        dest="randint_arg",
        nargs=2,
        type=int,
        metavar=("A", "B"),
        help="print a random integer in [A, B]",
    )
    parser.add_argument(
        "--bytes",
        type=int,
        metavar="N",
        help="print N random bytes as hex",
    )
    parser.add_argument(
        "--choice",
        nargs="+",
        metavar="ITEM",
        help="choose one item from the list",
    )
    parser.add_argument(
        "--pulses",
        type=int,
        default=1,
        metavar="N",
        help="fetch and print N consecutive beacon pulses",
    )
    args = parser.parse_args()

    rng = CURandom(chain_cid=args.chain_cid)
    for _ in range(args.pulses):
        pulse = rng.refresh()
        print(
            f"pulse round={pulse.round} index={pulse.index} "
            f"randomness={pulse.randomness_hex}"
        )

    if args.randint_arg:
        a, b = args.randint_arg
        print(f"randint({a}, {b}) = {rng.randint(a, b)}")
    if args.bytes:
        print(f"randbytes({args.bytes}) = {rng.randbytes(args.bytes).hex()}")
    if args.choice:
        print(f"choice({args.choice}) = {rng.choice(args.choice)}")

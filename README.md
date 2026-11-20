# CU-Random

**CU-Random** is a lightweight Python random-number generator powered by the **University of Colorado Boulder Randomness Beacon (CURBy)**. It retrieves the beacon’s latest public pulse and uses its 256-bit randomness value for random numbers, bytes, selections, shuffling, and other common tasks.

> Public randomness should not be treated as secret randomness. Because beacon pulses are publicly distributed, applications requiring unpredictable secrets should use Python’s `secrets` module or another cryptographically secure local entropy source.

## About CURBy

The [CU Boulder Randomness Beacon](https://random.colorado.edu/) is maintained as part of the work of the University of Colorado Boulder Department of Physics and partner institutions. CURBy publishes signed pulses of public randomness through a JSON API.

- Website: https://random.colorado.edu/
- API documentation: https://random.colorado.edu/api
- Department: https://www.colorado.edu/physics/
- University: https://www.colorado.edu/

## Features

- Uses the CU Boulder beacon API
- Standard-library only
- Random floats, integers, bytes, choices, and shuffling
- Automatic beacon refresh
- Optional fallback to Python’s `secrets` module
- Simple module-level convenience functions
- Command-line demonstrations
- No external package installation required

## Requirements

- Python 3.9 or newer
- Internet access for live beacon pulses
- No third-party Python dependencies

## Installation

Clone the repository:

```bash
git clone https://github.com/Akash7037/CU-Random.git
cd CU-Random
```

Run the module directly:

```bash
python cu_random.py
```

You can also copy `cu_random.py` into your project.

## Quick Start

```python
import cu_random as curandom

# Random float between 0.0 and 1.0
print(curandom.random())

# Random integer between 1 and 100, inclusive
print(curandom.randint(1, 100))

# Random choice
print(curandom.choice(["heads", "tails"]))

# Random bytes
print(curandom.randbytes(16).hex())

# Refresh entropy from the latest beacon pulse
pulse = curandom.refresh()
print(pulse.round)
print(pulse.randomness_hex)
``>

## Using `CURandom`

Create an independent generator:

```python
from cu_random import CURandom

rng = CURandom()

print(rng.random())
print(rng.randint(1, 100))
print(rng.choice(["python", "rust", "go"]))
print(rng.randbytes(32).hex())
print(rng.uniform(10.5, 20.5))
```

Inspect the latest successfully fetched pulse:

```python
pulse = rng.last_pulse

if pulse:
    print("Round:", pulse.round)
    print("Index:", pulse.index)
    print("Randomness:", pulse.randomness_hex)
    print("Chain:", pulse.chain)
    print("Signature:", pulse.signature)
``>

### Generate Random Integers

```python
rng = CURandom()

# Inclusive lower and upper bounds
dice_roll = rng.randint(1, 6)
print(dice_roll)
```

### Generate Random Bytes

```python
rng = CURandom()
random_bytes = rng.randbytes(32)

print(random_bytes.hex())
```

### Select an Item

```python
rng = CURandom()
color = rng.choice(["red", "green", "blue"])
print(color)
```

### Shuffle a List

```python
rng = CURandom()
cards = ["A", "2", "3", "4", "5"]

rng.shuffle(cards)
print(cards)
``>

### Generate a Gaussian Value

```python
rng = CURandom()

value = rng.gauss(mu=0.0, sigma=1.0)
print(value)
``>

> `gauss()` uses a local standard-library random number generator seeded by beacon randomness.

## Beacon Refresh and Fallback

Each instance fetches the latest pulse during initialization:

```python
rng = CURandom()
```

Fetch and use a fresh pulse manually:

```python
pulse = rng.refresh()
print(pulse.round)
```

By default, `CURandom` falls back to `secrets` when the beacon cannot be reached:

```python
rng = CURandom(fallback=True)
```

To disable fallback and let beacon errors propagate:

```python
rng = CURandom(fallback=False)
```

Set a custom timeout:

```python
rng = CURandom(timeout=5.0)
```

Use a custom API URL or chain:

```python
rng = CURandom(
    base_url="https://random.colorado.edu/api",
    chain_cid="YOUR_CHAIN_CID",
)
```

## Command-Line Usage

Print a random integer:

```bash
python cu_random.py --int 1 100
```

Print random bytes:

```bash
python cu_random.py --bytes 16
```

Choose from a list:

```bash
python cu_random.py --choice heads tails
```

Fetch one or more beacon pulses:

```bash
python cu_random.py --pulses 3
```

Combine options:

```bash
python cu_random.py --pulses 1 --int 1 6 --bytes 16 --choice heads tails
```

Example output:

```text
pulse round=123456 index=123456 randomness=<64-character-hex-value>
randint(1, 6) = 4
randbytes(16) = <32-character-hex-value>
choice(['heads', 'tails']) = heads
```

## API Details

CU-Random currently requests:

```text
GET /chains/{chainCid}/pulses/latest
```

The complete request URL is:

```text
https://random.colorado.edu/api/chains/{chainCid}/pulses/latest
``>

A parsed pulse includes:

| Field | Description |
|---|---|
| `cid` | CID of the pulse object |
| `chain` | CID of the pulse chain |
| `index` | Numeric index on the chain |
| `round` | Beacon round number |
| `randomness_hex` | 256-bit randomness as 64 hexadecimal characters |
| `previous_signature` | Signature of the previous round |
| `signature` | Signature of the current round |
| `source` | Source of the pulse |

Beacon responses use DAG-JSON, which is compatible with Python’s standard `json` parser.

## Security and Verification

The latest public pulse is suitable for demonstrations, simulations, games, lotteries, fair selection, testing, and many general-purpose applications.

For security-sensitive work:

- Verify the pulse and its signatures using an official beacon verification library.
- Check chain continuity and expected protocol rules.
- Do not assume public randomness is secret.
- Do not use public beacon output directly as passwords or private keys.
- Use `secrets.randbelow()` or `secrets.token_bytes()` for locally secure secrets.

This module fetches and consumes the `payload.randomness` value. Signature verification is intentionally left to the caller.

## Example: Dice Roller

```python
from cu_random import CURandom

rng = CURandom()

for _ in range(10):
    print(rng.randint(1, 6), end=" ")
```

## Example: Fair Team Selection

```python
from cu_random import CURandom

players = ["Aarav", "Maya", "Liam", "Nora", "Zoe"]
teams = {"Team A": [], "Team B": []}

rng = CURandom()

while players:
    player = rng.choice(players)
    players.remove(player)

    team = "Team A" if len(teams["Team A"]) <= len(teams["Team B"]) else "Team B"
    teams[team].append(player)

print(teams)
```

## Heartfelt Thanks and Contributions

This project is made possible by the researchers, scientists, engineers, and institutions who developed the CU Boulder Randomness Beacon, its Twine protocol, and its public research infrastructure.

Special thanks go to the CU Boulder Department of Physics and the people who created the CURBy API and classical and quantum randomness beacon work.

## Beacon Contributors

- **Jasper Palfree** — Twine protocol invention and implementation; CURBy API development; chain processes; website design and development.
- **Lynden K. Shalm** — Twine protocol; Bell experiment and data analysis; project supervision.
- **Gautam A. Kavuri** — Bell experiment and data analysis design and execution.
- **Aagam Dalal** — Twine protocol implementation.
- **Joseph M. Cavanagh** — Bell analysis implementation.
- **Luís T.A.N. Brandão** — Classical randomness beacon design.
- **Harold Booth** — Classical randomness beacon design.
- **René Peralta** — Classical randomness beacon design.
- **Katherine E. Stange** — Software development.
- **Paul D. Beale** — Software development.
- **Dileep V. Reddy** — Bell experiment detector development.
- **Yanbao Zhang** — Bell analysis implementation and development.
- **Joshua C. Bienfang** — Quantum Bell experiment hardware development.
- **Michael D. Mazurek** — Quantum Bell experiment hardware development.
- **Mohammad A. Alhejji** — Bell analysis implementation.
- **Aliza U. Siddiqui** — Bell analysis implementation.
- **Carlos Abellán** — Bell experiment hardware.
- **Waldimar Amaya** — Bell experiment hardware.
- **Morgan W. Mitchell** — Bell experiment hardware.
- **Sae Woo Nam** — Bell experiment design and implementation; project supervision.
- **Richard P. Mirin** — Project supervision.
- **Martin J. Stevens** — Bell experiment design and implementation; project supervision.
- **Emanuel Knill** — Bell analysis development and project supervision.

Thank you to these contributors for sharing knowledge and building infrastructure that makes public, verifiable randomness available to the wider community.

## Institutional Reference

Department of Physics  
390 UCB  
University of Colorado  
Boulder, CO 80309-0390  
United States

**Be Boulder.**

## References

- [CU Boulder Randomness Beacon](https://random.colorado.edu/)
- [CURBy API Documentation](https://random.colorado.edu/api)
- [University of Colorado Boulder](https://www.colorado.edu/)
- [Department of Physics at CU Boulder](https://www.colorado.edu/physics/)
- [Python Documentation: `random`](https://docs.python.org/3/library/random.html)
- [Python Documentation: `secrets`](https://docs.python.org/3/library/secrets.html)

## Project Structure

```text
CU-Random/
├── cu_random.py
└── README.md
```

## Contributing

Contributions are welcome.

Good ways to help:

- Improve API error handling
- Add pulse verification
- Add unit tests
- Improve CLI behavior
- Add usage examples
- Improve documentation
- Report issues or unexpected behavior

Before submitting a pull request:

1. Fork the repository.
2. Create a descriptive branch.
3. Make focused changes.
4. Test your changes.
5. Submit a pull request explaining what you changed.

## License

License terms have not yet been specified for this repository. Please review the beacon’s terms of use before deploying CURBy output in production or regulated applications.

## Acknowledgment

With deep appreciation to the University of Colorado Boulder, National Institute of Standards and Technology, Oak Ridge National Laboratory, and all partner institutions whose research, engineering, and careful collaboration helped make this project possible.

---

© Regents of the University of Colorado  
Privacy • Legal & Trademarks • Campus Map

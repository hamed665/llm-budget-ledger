# TokenLedger

**Atomic budget reservations and exact-decimal usage settlement.**

![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-green)

Stop concurrent inference requests from each spending the same remaining budget.

An original, runnable reference implementation by Hamed Minaei. Uses only the
Python standard library. No API key, paid account or network access is needed
for the included demos and tests. Version 0.1.0 focuses on the core engineering
contract rather than a hosted production service.

## Capabilities

- Integer micro-dollar persistence and Decimal price arithmetic
- Atomic reservations across independent SQLite connections
- Idempotent settlement and explicit release of unused holds
- Actual overruns remain visible and block subsequent spending
- Tenant-scoped budgets and configurable illustrative rates

## Quick start

```bash
git clone https://github.com/hamed665/llm-budget-ledger.git
cd llm-budget-ledger
python --version  # Python 3.11+
python -m tokenledger
python -m unittest discover -s tests -v
```

Optional library installation: `python -m pip install .`

## Use as a library

```python
from tokenledger.core import Ledger, estimate
l = Ledger("usage.db")
l.configure("demo", "5.00")
l.reserve("demo", "req-1", estimate(1000, 500, "2.50", "10"))
print(l.finish("demo", "req-1", 6000))
l.close()
```

## Data flow

Estimate → reserve transaction → external inference (adapter) → settle or release

See [tokenledger/core.py](tokenledger/core.py) for the implementation and [architecture notes](docs/architecture.md)
for transaction boundaries and deployment considerations.

## Verification

The test suite exercises behavioral guarantees, error paths and isolation.
SQLite projects also test competing connections with independent workers.
GitHub Actions runs the suite on Python 3.11, 3.12 and 3.13.
All fixtures are synthetic. Demo output is captured in
[examples/demo-output.txt](examples/demo-output.txt).

## Scope and limitations

No inference API is called. Example rates are illustrative, not current vendor pricing. This is a local ledger, not billing or payment processing. Reservations cannot guarantee upstream cost caps: settlement records actual overages. Callers must reconcile abandoned holds and provider usage. Use authenticated tenant mapping before any deployment.

## Repository map

- `tokenledger/`: importable library and runnable CLI demo
- `tests/`: regression and invariant tests
- `examples/`: synthetic inputs and captured demo output
- `docs/`: design decisions and boundaries
- `.github/workflows/ci.yml`: repeatable verification

## License

MIT. See [LICENSE](LICENSE). Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).

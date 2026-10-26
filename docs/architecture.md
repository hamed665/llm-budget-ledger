# Design notes — TokenLedger

## Contract

Stop concurrent inference requests from each spending the same remaining budget.

## Execution path

Estimate → reserve transaction → external inference (adapter) → settle or release

## Design choices

1. Integer micro-dollar persistence and Decimal price arithmetic.
2. Atomic reservations across independent SQLite connections.
3. Idempotent settlement and explicit release of unused holds.
4. Actual overruns remain visible and block subsequent spending.
5. Tenant-scoped budgets and configurable illustrative rates.

## Integration boundary

No inference API is called. Example rates are illustrative, not current vendor pricing. This is a local ledger, not billing or payment processing. Reservations cannot guarantee upstream cost caps: settlement records actual overages. Callers must reconcile abandoned holds and provider usage. Use authenticated tenant mapping before any deployment.

## Failure handling

Validation errors are explicit exceptions. SQLite mutations use bound SQL
parameters; multi-step mutations commit together or roll back. Library results
are data structures suitable for an adapter layer. No network calls or secrets
are embedded in the examples.

## Before deployment

Choose an authenticated adapter, add structured operational logging without raw
customer data, define backup and retention requirements, and test realistic
workloads. The local tests establish specific invariants; they do not establish
production throughput, external integration compatibility or service availability.

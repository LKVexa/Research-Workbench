# Workbench command and result contracts

Product version: **0.1.0-rc.1**. Foundation version: **0.1.0-rc.1**. Foundation manifest SHA-256: `e01d3f340239f4abe0daa27cb3e7c64190f95f4f3a0419f493bc14e7b07d571d`.

## Command interface

Global options precede the command:

```text
workbench.py [--state PATH] [--json] command [command options]
```

| Command | Arguments | Contract |
| --- | --- | --- |
| `menu` | None; also the default | Present the guided local menu |
| `doctor` | None | Check the installation and required runtime profile; report unavailable prerequisites |
| `catalog` | `--query TEXT`, `--executable`, `--collection COMP|TOPIC` | Filter catalog entries without changing their status or execution eligibility |
| `run` | `COMPONENT`, `--case CASE`, `--timeout SECONDS` | Execute one enabled, pinned capability in a new run directory |
| `verify` | Optional `RUN_ID`, optional `--fresh` | Check package/saved evidence; with a run ID, fresh verification performs a new execution |
| `resume` | `RUN_ID` | Recover interrupted or unsuccessful work through a linked attempt; refuse changed inputs/runtime and completed passing runs |
| `report` | None | Create a readable summary and identify its saved location |

Without `--state`, the history folder is `Local_Component_Workbench_State` beside the application folder. State must remain outside the installation and protected original roots. `--json` selects structured output for supported command results.

`D0001/C0081-03` accepts `baseline` and `negative-control`, defaulting to `baseline`. `D0007/C0322-01` and `D0007/C0322-02` accept `all`, `initial`, `correct`, and `regression`, defaulting to `all`. Timeout defaults to 30 seconds and must be between 0.05 and 60 seconds. Unknown components, unsupported cases, unavailable runtimes, and invalid requests are errors, not successful runs.

## Identity and evidence

A component ID includes its delivery, such as `D0007/C0322-02`. Catalog membership does not authorize execution. The catalog has 377 core COMP entries and 16 supporting TOPIC entries; exactly three are enabled in this release.

A run records a unique ID, component/case, timestamps, foundation version and manifest digest, baseline digest, interpreter identity, timeout, and any parent run ID. It retains the request, captured output, adapter result when available, final result, and integrity receipt. Report claims must resolve to these records.

Three current outcome fields remain distinct:

| Field | Meaning |
| --- | --- |
| `execution` | Whether the adapter operation completed successfully |
| `verification` | Whether the expected diagnostic checks and pinned result comparison passed |
| `scientific_validation` | Original research-method validation; `unverified` in this fixture release |

`candidate_accepted` is separate from those fields. A rejected regression or negative-control candidate can be the expected passing diagnostic result. Original pair statuses and G2 failures are preserved independently of every new run.

## Retry and compatibility

Run requests/results are not edited into new outcomes. An interrupted or unsuccessful run can have a linked retry. Repeated resume requests reuse the established child link rather than silently creating duplicate attempts. A completed passing run requires a new run or fresh verification to execute again.

Resume checks pinned package, input and interpreter identities. Changed dependencies do not inherit prior acceptance. A new product or foundation version is installed separately and qualified against its own manifest; an unchanged version number cannot waive a changed file hash.

This initial release uses foundation schema version 1.0.0 contracts. It does not promise compatibility with arbitrary future schemas, runtimes, third-party adapters, or scientific protocols.

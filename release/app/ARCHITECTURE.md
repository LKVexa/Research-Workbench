# Workbench architecture

The Local Component Workbench is a Windows application with a guided command menu and a command-line interface. It consumes a separately released shared foundation. The coding-agent platform and research toolkit have their own roots and remain deferred.

## Boundaries

| Part | Responsibility |
| --- | --- |
| Workbench.cmd | Select the configured Python interpreter and launch the application |
| workbench.py | Parse operator commands, display results, and produce workbench reports |
| Bundled foundation | Validate its package, expose the catalog, execute fixed adapters, and retain run evidence |
| Python adapter | Run D0001/C0081-03 baseline and negative-control fixtures |
| C# adapter | Run D0007/C0322-01 and C0322-02 diagnostics |
| Separate state directory | Store requests, results, logs, receipts, linked retries, and reports |

The product pins foundation **0.1.0-rc.1** by the SHA-256 of `foundation/MANIFEST.json`:

```text
e01d3f340239f4abe0daa27cb3e7c64190f95f4f3a0419f493bc14e7b07d571d
```

That is the inner foundation manifest digest, distinct from the outer foundation release-manifest digest. Do not replace files inside an accepted installation. A changed foundation requires a new product qualification and release.

## Run flow

The operator selects a registered component and case. The foundation verifies the package and runtime profile, creates a unique run directory, records the request and pinned identities, then starts the reviewed adapter with explicit arguments and bounded resources. It captures output, checks the adapter response, compares it with the case baseline, and commits the result and receipt.

Runs retain separate `execution`, `verification`, and `scientific_validation` outcomes. Candidate acceptance is another result: an intentionally faulty candidate should be rejected. Original status, original G2, and source limitations remain historical fields in the catalog.

The application stores new state outside its own installation and the protected original deliveries. It rejects path escapes and linked paths at the declared boundaries. Requests and results are preserved; retry coordination links a new attempt rather than rewriting a previous result into success.

## Trust and scope

Only three registered fixture capabilities are enabled. Imported titles, prompts, source text, and metadata cannot add commands. The runtime executes fixed, reviewed local adapters; it does not provide general containment for arbitrary hostile plugins. Limits and integrity checks support this bounded use model.

The catalog covers 393 entries and retains raw source references and normalized findings. Those records support discovery and provenance, not automatic execution. Source-only, blocked, failed, and otherwise unqualified entries remain disabled.

The application does not need the original D: delivery folders at runtime. Historical absolute paths can remain in provenance text. Portable copied evidence and pinned adapter files provide the runtime dependencies declared by this release.

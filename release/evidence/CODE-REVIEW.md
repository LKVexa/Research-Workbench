# Workbench code review

Scope: review of the local workbench application and its launchers before final packaging. This is a code review, not final clean-install or launcher execution evidence. The installed program and its manifest are trusted; the product does not claim authenticated execution of arbitrarily modified program code.

## Reviewed files

| File | SHA256 |
| --- | --- |
| workbench.py | afe8adcd732c9af56a5dd01c5254093a57408bdd37d4988d4ee279b210de9122 |
| Start-Workbench.ps1 | 46dccea306bcf01e35f08f33dfb38702b020ca6cabe453090b555ca54cf8e98a |
| Workbench.cmd | 0595bf056a30f1e132b327d0421fc1e5cebe786e43b8fed761bc73e81996a6df |

Pinned foundation manifest: `e01d3f340239f4abe0daa27cb3e7c64190f95f4f3a0419f493bc14e7b07d571d`.

## Findings and dispositions

1. **Resolved — reused resume could return false success.** The first reviewed implementation returned exit 0 whenever a resume link already existed, even if the linked attempt had failed. The reviewed revision resolves the child through `verify_run`, displays its actual result or incomplete state, and returns success only for verified passing execution. It retains the `resume_reused` and parent identity fields.
2. **Resolved — report column label.** The HTML table displayed `core`/`supporting` under a Collection heading. The revised heading is Role.
3. **Withdrawn — bytecode flag.** The initial review incorrectly identified `sys.dont_write_bytecode` as a typo. Inspection of the installed Python runtime confirms this is the correct attribute. Both launchers also pass `-B`. There is no bytecode-flag defect.

No unresolved code defect was found within the stated review scope after the above corrections.

## Reviewed behavior

- Product identity and exact foundation manifest hash are checked. The foundation performs its own complete file inventory and digest verification. The product rejects unexpected application files.
- User state is passed through the foundation path guard using the entire application root as protected. Original delivery roots remain protected. Default state lives beside the installation.
- Run and resume commands distinguish execution/verification from candidate acceptance. A known rejected regression can be a successfully verified diagnostic result.
- `verify --fresh` requires an identified intact completed evidence record and starts a new actual execution with linked parent identity. Ordinary verification checks saved evidence integrity and does not claim fresh execution.
- Report values are HTML-escaped, including errors and identifiers. Links are generated only for validated result paths. The document includes a restrictive Content Security Policy and no scripts.
- PowerShell passes interpreter and application arguments as separate values and invokes Python with `-I -B`. The batch entry forwards the operator's command-line arguments to that launcher. Final Windows launcher acceptance remains a packaging test.
- Source scientific outcomes remain separate from current operational checks and the three-product boundary remains intact.

## Release checks still required

Verify the exact final package in a moved directory with spaces. Exercise the Windows launcher, fresh verification, failed-run and reused-resume exit codes, report paths and rendering, preserved user evidence, and the documented first-release removal procedure. If reviewed source bytes change, re-evaluate affected behavior and update the recorded hashes.

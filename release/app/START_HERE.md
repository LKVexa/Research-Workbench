# Local Component Workbench

Version 0.1.0-rc.1

Use the workbench to browse the delivery catalog, run the supported local examples, and inspect their saved evidence. It contains **393 catalog entries: 377 core and 16 supporting**. Three entries are runnable through two adapters; the others remain visible with their limitations.

## Open the workbench

1. Extract the complete package into a normal writable folder.
2. Double-click **Workbench.cmd**. With no command supplied, it opens the guided menu.
3. Run **doctor** first to check the installation and required software.
4. Browse the catalog, then run a supported example. Keep the run ID shown in the result.
5. Use **verify** to check the saved evidence, and **report** to create a readable summary. Open the report at the path printed by the workbench.

Your run history is stored separately, in **Local_Component_Workbench_State** beside the application folder. Keep that folder when upgrading or removing the application. The workbench does not write to the original D0001–D0008 deliveries.

## Supported examples

| Component | What it demonstrates | Available cases |
| --- | --- | --- |
| D0001/C0081-03 | Assistant-token counting and rejection of an intentionally faulty counter | `baseline` (default), `negative-control` |
| D0007/C0322-01 | Bounded passing-test diagnostics | `all` (default), `initial`, `correct`, `regression` |
| D0007/C0322-02 | Preservation of previously passing tests | `all` (default), `initial`, `correct`, `regression` |

A negative control is deliberately wrong. A successful diagnostic should reject it. For example, the `regression` case should report that the candidate was not accepted even when execution and verification pass.

## Read the results correctly

Three current results answer different questions:

- **Execution:** did the selected local example run successfully?
- **Verification:** did its checks and saved result match the pinned baseline?
- **Scientific validation:** was the original research method validated? This release reports **unverified** for that broader claim.

The catalog also retains the original delivery status. All eight historical G2 gates remain failed. A fresh local example does not change those records. The catalog preserves 130 audit findings and identifies 209 entries that contain source intake only.

## Commands

From PowerShell opened in the application folder, use the launcher:

```powershell
.\Workbench.cmd doctor
.\Workbench.cmd catalog --executable
.\Workbench.cmd catalog --query C0322 --collection COMP
.\Workbench.cmd run D0001/C0081-03 --case baseline
.\Workbench.cmd run D0007/C0322-02 --case regression
.\Workbench.cmd verify RUN_ID
.\Workbench.cmd verify RUN_ID --fresh
.\Workbench.cmd resume RUN_ID
.\Workbench.cmd report
```

Replace `RUN_ID` with the ID of your run. `verify --fresh` with a run ID performs another execution. `resume` is for interrupted or unsuccessful work and creates or reuses a linked attempt. Passing completed runs stay unchanged; use a new run or fresh verification to repeat them.

Put global options before the command. To choose a different history folder or request JSON output:

```powershell
.\Workbench.cmd --state "E:\Workbench Runs" catalog --executable
.\Workbench.cmd --json doctor
```

For direct use with the required interpreter, the interface is:

```text
workbench.py [--state PATH] [--json] command
```

Commands are `menu` (the default), `doctor`, `catalog`, `run`, `verify`, `resume`, and `report`. `run` accepts `--timeout SECONDS`; the supported range is 0.05–60 seconds, with 30 seconds as the default.

## If startup or a run fails

The tested profile is Windows with **Python 3.12.14, NumPy 2.3.5, and .NET Framework**. These runtime dependencies are not bundled. No other operating system or runtime combination is claimed as tested.

The launcher first uses `WORKBENCH_PYTHON` if set, then the existing Codex-bundled Python location, then `python` on PATH. If Windows opens a Store prompt or the wrong interpreter is selected, set `WORKBENCH_PYTHON` to the full path of the required Python executable and reopen the launcher. Run `doctor` again before attempting a component.

If verification reports changed or missing files, retain the evidence and restore a clean copy of the package. Do not edit checksums or delete a failed run to make verification pass. A disabled catalog entry requires further implementation or qualification; it cannot be enabled by changing its displayed status.

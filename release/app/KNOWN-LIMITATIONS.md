# Known limitations

This release supports a small executable profile within a larger catalog. It has **393 entries and three runnable capabilities**. The remaining 390 entries are disabled. Of the core entries, 209 contain source intake only; their presence does not establish an implemented method.

The runnable capabilities are bounded authored fixtures: one Python token-counting example and two C# passing-test/regression diagnostics. Passing their checks does not reproduce an original paper at scale. `scientific_validation` remains `unverified`, and all historical product G2 failures remain unchanged.

The catalog retains **130 audit findings**: 84 aggregate-count differences, 26 D0006 result-text discrepancies, and 20 D0008 missing-document groups. Normalized reporting preserves the originals rather than silently repairing their historical records.

The observed tested runtime profile is **Windows, Python 3.12.14, NumPy 2.3.5, and .NET Framework**. Runtime dependencies are not redistributed. Other operating systems and runtime combinations have not been established by this release's evidence. The launcher searches for an existing interpreter; it does not install Python or packages.

Execution is restricted to reviewed, pinned adapters. The workbench does not run arbitrary commands from imported documents and does not claim operating-system containment for arbitrary hostile plugins. Resource and integrity checks apply to the declared local fixture workflow.

The first release provides a local menu and command-line interface. It does not include a hosted service, model provider, repository-solving agent, training pipeline, GPU experiment suite, or automatic scientific implementation. The coding-agent platform and research toolkit remain separate future products.

Saved provenance can contain original absolute paths. Those paths describe history; runtime use depends on the packaged files and declared local prerequisites. Package integrity and evidence checks should be repeated after moving an installation or changing its environment.

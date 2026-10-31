# Upgrade, rollback, and removal

The application folder and run-history folder are separate. Preserve **Local_Component_Workbench_State**, or the folder you chose with `--state`, before changing installations. It contains your run evidence and reports.

## Upgrade

1. Finish or stop active runs and close the workbench.
2. Keep the existing application folder. Extract a new release into a different folder.
3. Launch the new release and run `doctor` before using it.
4. Choose the intended state folder explicitly if the new installation has a different parent folder.
5. Keep the old release until the new release's documented checks pass.

Do not copy new files over an accepted installation. Each release pins its own foundation and package identities. Historical results remain associated with their original versions.

## Roll back

Close the new release, reopen the previous release's `Workbench.cmd`, and select the state folder used with that release. Run `doctor` and verify a saved run before continuing.

If the package or interpreter identity differs from a saved request, resume can refuse it. Preserve the old run and start a new explicit run under the intended version; do not edit hashes or request files to bypass the check. This first release has no earlier supported workbench version and performs no automatic state migration.

## Remove the first release

Close the workbench and confirm no run remains active. Remove only the extracted application folder using Windows File Explorer. Keep the separate state folder if you want to retain evidence. Removing this application does not require deleting or restoring any D0001–D0008 delivery.

If you later remove the state folder, its run history and reports are lost. Treat that as a separate, deliberate decision.

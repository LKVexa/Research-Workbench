param([Parameter(ValueFromRemainingArguments=$true)][string[]]$WorkbenchArguments)
$ErrorActionPreference = 'Stop'
$candidates = @()
if ($env:WORKBENCH_PYTHON) { $candidates += $env:WORKBENCH_PYTHON }
$profileFolder = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
$candidates += Join-Path $profileFolder '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$foundPython = Get-Command python.exe -ErrorAction SilentlyContinue
if ($foundPython) { $candidates += $foundPython.Source }
$selectedPython = $null
foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        if ($candidate -like '*WindowsApps*') { continue }
        $selectedPython = $candidate
        break
    }
}
if (-not $selectedPython) {
    Write-Error 'No usable Python found. Set WORKBENCH_PYTHON to Python 3.12.14 with NumPy 2.3.5; see START_HERE.md.'
    exit 2
}
& $selectedPython -I -B (Join-Path $PSScriptRoot 'workbench.py') @WorkbenchArguments
exit $LASTEXITCODE

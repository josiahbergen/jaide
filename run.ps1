$ErrorActionPreference = 'Stop'

Push-Location $PSScriptRoot
try {
    Clear-Host
    uv run -m jasm kernel/boot.jasm --output bin/boot.bin --nolink --nowarn -v 2
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    uv run -m emulator bin/boot.bin --rtc --graphics --memory --disk --image jfs/images/disk.img -r -v 2
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

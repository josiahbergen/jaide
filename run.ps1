$ErrorActionPreference = 'Stop'

Push-Location $PSScriptRoot
try {
    Clear-Host
    uv run -m jasm kernel/boot.jasm --output bin/boot.bin --nolink --nowarn -v 0
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    uv run -m emulator bin/boot.bin --rtc --graphics --disk --image jfs/images/disk.img -r
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

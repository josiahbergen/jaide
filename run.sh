#!/usr/bin/env bash
set -e

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
clear
uv run -m jasm kernel/boot.jasm --output bin/boot.bin --nolink --nowarn
exec uv run -m emulator bin/boot.bin --rtc --graphics --disk --image jfs/images/disk.img -r

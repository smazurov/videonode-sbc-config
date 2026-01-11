# videonode-sbc-config

SBC configuration for videonode streaming. Currently supports Rockchip RK3588 on Armbian.

## Development

- Run commands through uv: `uv run videonode-sbc-config setup`
- Lint/format: `uv run ruff check --fix src/ && uv run ruff format src/`
- Type check: `uv run pyright src/`
- Test locally before pushing

## Project Structure

```
src/videonode_sbc_config/
├── cli.py                      # CLI entry point with platform detection
├── platform/                   # Platform detection layer
│   ├── types.py                # SBCFamily, OSType, SBCModel enums
│   └── detect.py               # Detection logic
└── deploys/
    ├── generic/                # Cross-platform deploys (any Debian-based)
    ├── os/<os_name>/           # OS-specific deploys
    ├── hardware/<sbc_family>/  # Hardware acceleration stacks
    └── verify/                 # Platform-specific verification
```

## Adding New Platform Support

### New SBC Family (e.g., Raspberry Pi)

1. Add enum values in `platform/types.py`:
   - `SBCFamily.RASPBERRY_PI`
   - `SBCModel.RPI4`, `SBCModel.RPI5`

2. Add detection in `platform/detect.py`:
   - Check `/proc/device-tree/compatible` for `bcm2` or model string

3. Create hardware stack in `deploys/hardware/rpi/`:
   - `ffmpeg.py` - FFmpeg with V4L2/VideoCore
   - `permissions.py` - Video group, GPU memory
   - `stack.py` - Orchestrator

4. Create verification in `deploys/verify/rpi_<os>.py`

5. Update `cli.py` to dispatch based on detected platform

### New OS (e.g., DietPi)

1. Add `OSType.DIETPI` in `platform/types.py`

2. Add detection in `platform/detect.py`:
   - Check for `/boot/dietpi.txt`

3. Create OS-specific deploys in `deploys/os/dietpi/`:
   - `kernel_overlays.py` - DietPi overlay mechanism

4. Update verification to handle the new OS

## Deploys

Pyinfra scripts run with `@local` connector. Organization:

- `generic/` - Works on any Debian-based OS (cockpit, alloy)
- `os/<name>/` - OS-specific tooling (armbian-add-overlay)
- `hardware/<family>/` - SBC-specific acceleration (MPP/RGA for Rockchip)
- `verify/` - Platform-specific verification checks

## Git Commits

Conventional format: `<type>(<scope>): <subject>`

- Types: feat|fix|docs|style|refactor|test|chore|perf
- Subject: 50 chars max, imperative mood, no period

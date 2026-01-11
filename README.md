# videonode-sbc-config

Rockchip RK3588 SBC configuration for [videonode](https://github.com/smazurov/videonode).

## Prerequisites

- RK3588-based SBC with Armbian
- [uv](https://docs.astral.sh/uv/) installed

## Installation

Install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Usage

Run hardware setup:

```bash
uvx git+https://github.com/smazurov/videonode-sbc-config setup
```

Check status:

```bash
uvx git+https://github.com/smazurov/videonode-sbc-config status
```

Setup Grafana Alloy metrics:

```bash
uvx git+https://github.com/smazurov/videonode-sbc-config alloy \
    --token <TOKEN> --username <USER_ID> --url <PROMETHEUS_PUSH_URL>
```

## What it configures

- FFmpeg with Rockchip hardware acceleration (MPP, RGA)
- Device permissions for hardware encoders
- Kernel overlays (USB host mode, disable HDMI RX)
- Cockpit web management

## Development

### Adding New SBC Support

The codebase is organized for extensibility:

```
src/videonode_sbc_config/
├── platform/                   # Platform detection
│   ├── types.py                # SBCFamily, OSType, SBCModel enums
│   └── detect.py               # Detection logic
└── deploys/
    ├── generic/                # Cross-platform (cockpit, alloy)
    ├── os/<os_name>/           # OS-specific (kernel overlays)
    ├── hardware/<sbc_family>/  # Hardware acceleration stack
    └── verify/                 # Verification checks
```

To add a new SBC family (e.g., Raspberry Pi):

1. Add enums in `platform/types.py` (`SBCFamily.RASPBERRY_PI`, `SBCModel.RPI5`)
2. Add detection in `platform/detect.py`
3. Create `deploys/hardware/rpi/` with FFmpeg and permissions scripts
4. Create `deploys/verify/rpi_<os>.py`
5. Update `cli.py` dispatch logic

To add a new OS (e.g., DietPi):

1. Add `OSType.DIETPI` in `platform/types.py`
2. Add detection in `platform/detect.py`
3. Create `deploys/os/dietpi/` with OS-specific scripts
4. Update verification for the new OS

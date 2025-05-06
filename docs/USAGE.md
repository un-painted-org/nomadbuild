# Using NomadBuild

This guide expands on the quick-start commands from the main README.

## Prerequisites

* Docker Desktop or Docker Engine running.
* A Bitaxe device on the same LAN.

## Common Commands

| Goal | Command |
| --- | --- |
| Build Docker image | `./nomadbuild.sh --build-image` |
| Clean firmware files and rebuild Docker image | `./nomadbuild.sh --build-image clean` |
| Launch Web-UI | `./nomadbuild.sh --webui` |
| Build latest stable tag (CLI) | `./nomadbuild.sh --build` |
| Build specific tag | `./nomadbuild.sh --tag v2.7.0` |
| Flash device after build | `./nomadbuild.sh --flash-ip 192.168.1.100` |
| Force flash without prompt | `./nomadbuild.sh --tag v2.7.0 --flash-ip 192.168.1.100 --force-flash` |

Windows users: run these commands from WSL or any Linux compatibility layer and access the Web-UI via browser.

## Artifact Locations

After a successful build you will find:

* `firmware/esp-miner-<TAG>.bin` – merged firmware binary
* `firmware/www-<TAG>.bin` – web interface bundle
* `firmware/build.log` – build log

## Reproducibility Check

```bash
./nomadbuild.sh --repro --tag v2.7.0
```

Runs two consecutive builds inside Docker and compares SHA-256 hashes of generated binaries.

## Troubleshooting

* **Build fails** – ensure internet connectivity; rerun `--build-image` if toolchain image is outdated.
* **Flash fails** – verify IP address, make sure device and host are on same network.
* **Port 9090 busy** – pass `--restart-webui` to stop existing container.
* **After upgrading** – use `--build-image clean` to ensure you're using a fresh Docker image and clean firmware directory after upgrading to a new nomadbuild release.

## CSV-Based Flashing

You can flash multiple devices at once using a CSV file:

```bash
./nomadbuild.sh --tag v2.7.0 --flash-csv devices.csv
```

**Note**: The `--flash-csv` and `--flash-ip` options are mutually exclusive. Use `--flash-ip` for a single device or `--flash-csv` for multiple devices. The `--flash-ip` option only accepts a single IP address.

The CSV file should contain one IP address per line. Comments (lines starting with #) and empty lines are ignored.

Example CSV file:
```
# Living room devices
192.168.1.100
192.168.1.101

# Office devices
192.168.1.102
```

The CSV file can be located anywhere on your system - it will be copied into the container for processing.

### Important Notes on Flashing

- The system performs strict device verification before flashing to ensure compatibility
- Each device is verified to be a supported Bitaxe model
- The system will detect and report network connectivity issues
- After flashing, the system verifies that the device comes back online with the expected firmware version
- For multiple devices, you'll be asked for batch confirmation before proceeding
# Using NomadBuild

This guide expands on the quick-start commands from the main README.

## Prerequisites

* Docker Desktop or Docker Engine running.
* A Bitaxe device on the same LAN.

## Common Commands

| Goal | Command |
| --- | --- |
| Build Docker image | `./nomadbuild.sh --build-image` |
| Clean and rebuild Docker image | `./nomadbuild.sh --build-image clean` |
| Launch Web-UI | `./nomadbuild.sh --webui` |
| Build latest stable tag (CLI) | `./nomadbuild.sh --build` |
| Build specific tag | `./nomadbuild.sh --tag v2.6.3` |
| Flash device after build | `./nomadbuild.sh --flash-ip 192.168.1.100` |
| Force flash without prompt | `./nomadbuild.sh --tag v2.6.3 --flash-ip 192.168.1.100 --force-flash` |

Windows users: run these commands from WSL or any Linux compatibility layer and access the Web-UI via browser.

## Artifact Locations

After a successful build you will find:

* `firmware/esp-miner-<TAG>.bin` – merged firmware binary
* `firmware/www-<TAG>.bin` – web interface bundle
* `firmware/build.log` – build log

## Reproducibility Check

```bash
./scripts/repro.sh --tag v2.6.3
```

Runs two consecutive builds inside Docker and compares SHA-256 hashes of generated binaries.

## Troubleshooting

* **Build fails** – ensure internet connectivity; rerun `--build-image` if toolchain image is outdated.
* **Flash fails** – verify IP address, make sure device and host are on same network.
* **Port 9090 busy** – pass `--restart-webui` to stop existing container.
* **After upgrading** – use `--build-image clean` to ensure you're using a fresh Docker image after upgrading to a new nomadbuild release.
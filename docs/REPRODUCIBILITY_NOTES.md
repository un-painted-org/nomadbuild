# Notes on Reproducible Builds for ESP-Miner

## A note on the Bitaxe Factory Images?

The Official Bitaxe "factory" binaries embed device-specific offsets and other data; upstream does not publish a generic merged image.  Therefore byte-for-byte identity with factory releases is not expected.

## Methodology of Reproducible Builds in Nomadbuild

* **Controlled Environment:** Builds run inside the `nomadbuild` Docker image (based on `espressif/idf:v5.4.1`). This locks compiler, ESP-IDF, Python and system paths.
* **Dependency Pinning:** The `Dockerfile` pins the base image (`espressif/idf:v5.4.1`), Python packages (`pip`), and system packages (`apt`) to specific versions defined in `build/apt_pins.conf`. APT pinning preferences (`/etc/apt/preferences.d/`) are used to enforce system package versions.
* **Version Verification:** A script (`scripts/verify_pinned_versions.sh`) runs during the Docker build to confirm that all specified package versions were installed correctly, failing the build on mismatch.
* **Fixed Source:** `scripts/repro_builder.py` clones **upstream** `bitaxeorg/ESP-Miner` and checks out the exact git tag passed to the `--repro` command.
* **Timestamp Control:** The commit timestamp of that tag is exported as `SOURCE_DATE_EPOCH`, allowing ESP-IDF to embed deterministic timestamps.
* **Clean Builds:** Each run executes `idf.py fullclean` to purge artefacts before building.
* **Generic Merged Binary:** After build, upstream `merge_bin.sh` combines bootloader, app, partitions, www and OTA images into a single `merged-<tag>.bin`.
* **Hashing:** We calculate SHA-256 of that merged binary.
* **Two-Pass Comparison (`./nomadbuild.sh --repro --tag <tag>`):** The script runs the entire sequence twice inside the same container and compares the hashes.

## Findings

* **Internal reproducibility:** For tags ≥`v2.6.3` (including the latest `v2.7.0`), both runs produce identical hashes (`MATCH`). This holds across different hosts as long as the same `nomadbuild` image is used.
* **Cross-machine reproducibility:** Users on macOS, Linux and Windows (WSL) have reproduced identical hashes when using the Docker image.

## Remaining Non-Determinism Risks

* Future ESP-IDF updates might introduce random UUIDs.  Locking the Docker base image mitigates this.
* Updates to the NodeSource repository could introduce newer patch versions for `nodejs` than the one pinned in `build/apt_pins.conf`. The build will use the pinned version, but awareness of newer releases might be needed.
* Absolute build path must stay `/app/...`; our Dockerfile enforces that.

## Conclusion

With the help of the `--repro` command **anyone** can independently build an upstream ESP-Miner firmware for a given tag and verify internal reproducibility of the resulting generic merged binary. This offers strong assurance that binaries produced by NomadBuild match the public source, even though they may differ from Bitaxe factory releases.
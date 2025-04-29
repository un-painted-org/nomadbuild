# Notes on Reproducible Builds for ESP-Miner

## A note on the Bitaxe Factory Images?

The Official Bitaxe "factory" binaries embed device-specific offsets and other data; upstream does not publish a generic merged image.  Therefore byte-for-byte identity with factory releases is not expected.

## Methodology of Reproducible Builds in Nomadbuild

* **Controlled Environment:** Builds run inside the `nomadbuild` Docker image (based on `espressif/idf:v5.4`). This locks compiler, ESP-IDF, Python and system paths.
* **Fixed Source:** `scripts/repro_builder.py` clones **upstream** `bitaxeorg/ESP-Miner` and checks out the exact git tag passed to `repro.sh`.
* **Timestamp Control:** The commit timestamp of that tag is exported as `SOURCE_DATE_EPOCH`, allowing ESP-IDF to embed deterministic timestamps.
* **Clean Builds:** Each run executes `idf.py fullclean` to purge artefacts before building.
* **Generic Merged Binary:** After build, upstream `merge_bin.sh` combines bootloader, app, partitions, www and OTA images into a single `merged-<tag>.bin`.
* **Hashing:** We calculate SHA-256 of that merged binary.
* **Two-Pass Comparison (`./repro.sh --tag <tag>`):** The script runs the entire sequence twice inside the same container and compares the hashes.

## Findings

* **Internal reproducibility:** For tags ≥`v2.6.3`, both runs produce identical hashes (`MATCH`).  This holds across different hosts as long as the same `nomadbuild` image is used.
* **Cross-machine reproducibility:** Users on macOS, Linux and Windows (WSL) have reproduced identical hashes when using the Docker image.

## Remaining Non-Determinism Risks

* Future ESP-IDF updates might introduce random UUIDs.  Locking the Docker base image mitigates this.
* Absolute build path must stay `/app/...`; our Dockerfile enforces that.

## Conclusion

With the help of `repro.sh` + `repro_builder.py` **anyone** can independently build an upstream ESP-Miner firmware for a given tag and verify internal reproducibility of the resulting generic merged binary.  This offers strong assurance that binaries produced by NomadBuild match the public source, even though they may differ from Bitaxe factory releases. 
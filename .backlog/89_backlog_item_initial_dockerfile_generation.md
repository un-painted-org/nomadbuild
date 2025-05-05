# Backlog Item 89:Templated Dockerfile Generation with Reproducibility Focus

**Description:**

This Python script (`generate_dockerfile.py`) is the first step in creating a reproducible build environment for the "nomadbuild" project. The script reads a comprehensive `config.yaml` file and generates a `Dockerfile` that ensures pinned versions for both system (APT) and Python packages, along with essential OS configurations to guarantee consistent build outcomes. The primary goal is to achieve a high level of reproducibility in the container image's build environment.

**Background:**

The "nomadbuild" project aims for a reproducible build environment to avoid issues caused by changing package versions or environmental inconsistencies. This initial phase focuses on generating a `Dockerfile` that pins the base image using its SHA256 digest and ensures that all necessary APT and Python packages are installed at specific versions. We will achieve APT pinning through the use of preference files and direct `apt-get install` commands with exact versions. Python packages will be pinned using `pip install` within a virtual environment. Additionally, the `Dockerfile` will set specific environment variables to lock down locale, timezone, and Python's hash behavior.

**Requirements:**

* **Configuration File:** The script must read all necessary configuration details from a single, human-readable `config.yaml` file. This file will include sections for:
    * `base_image`: Specifying the Docker image name and its SHA256 digest.
    * `os_config`: Defining environment variables for timezone (`TZ`), locale (`LC_ALL`, `LANG`), and Python hash seed (`PYTHONHASHSEED`).
    * `apt_packages`: A list of APT packages with their exact versions to be pinned.
    * `python_packages`: A list of Python packages with their exact versions.
* **Digest-Pinned Base Image:** The generated `Dockerfile`'s `FROM` line must use the SHA256 digest specified in the `config.yaml` to ensure immutability of the base image.
* **APT Pinning:** For every package listed under `apt_packages` in the `config.yaml`, the generated `Dockerfile` must:
    * Create an APT preference pin file in `/etc/apt/preferences.d/` with the exact version and a high priority (e.g., 1001).
    * Include the package name in the `apt-get install -y --no-install-recommends` command.
* **Python Pinning:** All Python packages listed under `python_packages` in the `config.yaml` must be installed within a virtual environment using `pip install` with exact `==` version specifiers.
* **Environment Fixed:** The generated `Dockerfile` must contain `ENV` instructions to set `LC_ALL=C.UTF-8`, `LANG=C.UTF-8`, `TZ=UTC`, and `PYTHONHASHSEED=0` to ensure a consistent environment.
* **Config-Driven Output:** The `generate_dockerfile.py` script must fully produce the `Dockerfile` based solely on the input `config.yaml`. Any changes to the generated `Dockerfile` should only occur through modifications to the `config.yaml` file.

**Acceptance Criteria:**

* **Digest-Pinned Base:** The generated `Dockerfile`’s `FROM` line uses the SHA256 digest from the `config.yaml`.
* **APT Pinning:** For every package in the `apt_packages` section of the `config.yaml`, the `Dockerfile` includes:
    * Commands to create a preference file in `/etc/apt/preferences.d/` pinning the exact version with high priority.
    * The package name in the `apt-get install` command.
* **Python Pinning:** All packages in the `python_packages` section of the `config.yaml` are installed using `pip install {name}=={version}` within a virtual environment created in the `Dockerfile`.
* **Environment Fixed:** The `Dockerfile` contains `ENV LC_ALL=C.UTF-8`, `ENV LANG=C.UTF-8`, `ENV TZ=UTC`, and `ENV PYTHONHASHSEED=0`.
* **Config-Driven Output:** The `generate_dockerfile.py` script generates the complete `Dockerfile` based on the `config.yaml`. Modifying the `config.yaml` is the only way to alter the generated `Dockerfile` regarding the base image, OS environment, and pinned package versions.

Please replace the content of your local `config.yaml` with the code block above. The `generate_dockerfile.py` script remains the same for now. We will modify it in the next step to incorporate the logic for APT and Python package pinning based on this comprehensive configuration.
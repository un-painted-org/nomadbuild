# NOMADBUILD Project Backlog

> **IMPORTANT RULE**: Items in this backlog MUST NOT be marked as "Completed" unless explicitly instructed by the project owner. All status changes require direct approval.
YOU ARE MARKING NOTHING AS COMPLETED YOURSELF UNLESS TOLD OTHERWISE. YOU MUST NOT ACT ON YOUR OWN ON BACKLOG ITEM STATUS UPDATES UNLESS I ALLOW IT FOR A SPECIFIC ITEM. YOU MUST ONLY WORK ON A SINGLE BACKLOG ITEM AT A TIME.

## Open Items (Sorted by Priority)

### Critical Priority

57. **Implement Support for NerdQAxe Product Family** - *Not Started*
   - Integrate support for building firmware compatible with the NerdQAxe product family, utilizing the firmware fork at [`https://github.com/shufps/ESP-Miner-NerdQAxePlus`](https://github.com/shufps/ESP-Miner-NerdQAxePlus).
   - User interface should feature visual tiles with device images for selecting the target device (Bitaxe or NerdQAxe). Alternatively, prompt user for device type after clicking build, before starting work.
   - The build interface should adapt for the selected device family where necessary, while generalizing common build steps.
   - Implement logic to select and use the correct Git repository based on device selection.
   - Analyze and integrate device-specific build commands, `idf.py` targets, partition table usage, and post-build scripts (e.g., binary merging).
   - Adapt configuration handling to support device-specific requirements.
   - Update the build interface to provide clear feedback on the selected device and build progress.
   - Implement comprehensive error handling for device-specific operations.
   - Document the process for building NerdQAxe firmware.
   - **Device Detection:** Implement accurate device detection logic before flashing to prevent flashing incorrect firmware.
     - **Identification Priority:**
       1. Check `deviceModel` (if available)
       2. If `deviceModel` is absent, check `minerModel`
       3. If neither are present, use `boardVersion`
       4. If still unsure verify known `ASICModel` details
       5. If STILL unsure, ask the user. Never flash if not 100% certain!
     - **NerdQAxe++ Details:**
       | Model Name         | boardVersion | deviceModel String | minerModel String |
       |--------------------|-------------|---------------------|-------------------|
       | NerdQAxe++         | N/A         | `"NerdQAxe++"`      | N/A               |
   - Add or update relevant test cases.

### High Priority

56. **Clean Up Scripts Organization** - *Needs Verification*
   - Moved redundant `run_tests.sh` to the archive directory (it was just a wrapper for `scripts/test.sh`).
   - Moved `download_vendors.sh` from project root to the `scripts/` directory for better organization.
   - Updated Dockerfile references to the new `scripts/download_vendors.sh` path.
   - Added missing `handle_clear_log` function to `src/web_ui.py` to fix related test failures.
   - Note: Import errors related to `src` when running pytest locally are likely environment issues; tests pass via `scripts/test.sh`.

60. **Fix Skipped Process Tracking Test** - *Not Started*
   - Test `test_run_idf_build_tracks_active_processes` in `src/tests/test_builder_build.py` is currently skipped (`@pytest.mark.skip`).
   - The test persistently fails to verify that the mocked process is added to the `active_build_processes` dictionary during threaded execution.
   - Multiple attempts to fix via timing adjustments, explicit imports, using PID as key, and process-poll side effects were unsuccessful.
   - Requires deeper investigation into mocking interactions with threading and global state, or a different testing approach.

62. **Codebase Cleanup: Remove Obsolete Comments and Deprecated/Commented-Out Code** - *Not Started*
   - **Description:**
   - Perform a comprehensive review of the entire codebase (including shell scripts, Python files, HTML templates, JS, CSS, etc.) to identify and remove any commented-out code sections, deprecated function markers, or obsolete comments that are no longer relevant or were left behind during previous refactoring/development efforts. This ensures code clarity and reduces potential confusion.

63. **Refactor: Consolidate Artifact Handling** - *Not Started*
   - **Description:** The logic for copying build artifacts (`copy_artifacts_to_output` in `utils.py`) and creating/saving the `build_info.json` (`create_and_save_build_info` in `utils.py`) is currently called separately by both the CLI (`cli.py`) and the Web UI (`web_ui.py`). Consolidate these steps into a single, reusable function or class method within the `builder` package to avoid duplication and ensure consistency.
   - **Acceptance Criteria:**
     - A single function handles artifact copying, `build_info.json` creation, and saving.
     - Both `cli.py` and `web_ui.py` call this consolidated function.
     - Existing build/flash functionality remains unchanged for both interfaces.
     - Add/update relevant unit tests to cover the consolidated function and its usage.

64. **Refactor: Unify Build Process Invocation** - *Not Started*
   - **Description:** The core build sequence (`idf clean`, `prepare source`, `idf build`, `verify artifacts`, `find outputs`) defined in `build_esp_miner` (`build.py`) is invoked slightly differently by the CLI and Web UI, particularly regarding argument passing and progress reporting. Refactor the entry points in `cli.py` and `web_ui.py` to call the build orchestration logic in a more unified way, potentially using a shared helper function or class.
   - **Acceptance Criteria:**
     - CLI and Web UI use a common mechanism to initiate the build process defined in `build.py`.
     - Handling of parameters like `selected_tag`, `verbose_stream`, and `progress_callback` is standardized.
     - Build functionality remains unchanged.
     - Add/update relevant unit/integration tests to cover the unified invocation logic.

76. **Add Direct Link to Official Bitaxe Web Flasher** - *Not Started*
   - Provide an easily accessible hyperlink in the Web-UI that opens the official online flasher at <https://bitaxeorg.github.io/bitaxe-web-flasher/>.
   - Location: Flashing section or a dedicated "Alternative Flash Methods" panel.
   - Ensure the link opens in a new browser tab and is clearly labelled as "Official Bitaxe Web Flasher".
   - Update documentation/help text accordingly.

77. **Add Direct Link to NerdQAxe Web Flasher (blocked until device support)** - *Not Started*
   - Same UX as above but pointing to <https://shufps.github.io/nerdqaxe-web-flasher/>.
   - This backlog item is dependent on #57 (NerdQAxe support). The link should be hidden or disabled until NerdQAxe build/flash support is implemented.
   - Update tests once the feature flag/conditional display is in place.

78. **Automated Docker Image Build for Tagged Releases** - *Not Started*
   - Create a GitHub Actions workflow that triggers on new Git **tags** pushed to the `main` branch (stable releases).
   - Workflow steps:
     1. Check out code and set up QEMU/Buildx for multi-arch builds if feasible.
     2. Build the NomadBuild Docker image (using the project's Dockerfile).
     3. Ensure *all* runtime scripts (`scripts/entrypoint_wrapper.sh`, build helpers, etc.) are included inside the image so users can run it without the repo.
     4. Push the image to GitHub Container Registry (ghcr.io) and/or Docker Hub with tag name equal to the Git tag (e.g., `v2.6.3`).
   - Refactor: keep only a thin `nomadbuild.sh` wrapper outside the image; move other host-expected files into the image context.
   - Acceptance criteria:
     - Tagged workflow produces a downloadable container image for every release.
     - Minimal host script still launches the container correctly across OSes (Linux/macOS/Windows with Docker Desktop).
     - CI passes on pull-requests; workflow only pushes on tags.
     - Documentation updated.

79. **Improve Build Cancellation UX Clarity** - *Not Started*
  - Users have reported confusion about what happens when they cancel a build via the UI.
  - Update the web UI and CLI messaging to clearly indicate the cancellation progression and final state.
  - Acceptance Criteria:
    - Cancel button becomes disabled and label changes to "Cancelled" immediately upon user action.
    - A confirmation toast/modal appears summarizing that the build has been halted and no further operations will run.
    - Build progress bar resets or displays a distinct "Cancelled at X%" state with appropriate styling.
    - Documentation in `docs/USAGE.md` is updated to describe cancellation behavior.
    - Unit/integration tests added to cover the new UI states and messages.

### Medium Priority

70. **Add Web UI Server Endpoint & Socket.IO Tests** - *Not Started*
   - Use Flask test client and Socket.IO test client to hit `/api/build`, verify status emissions, and error handling.

72. **Stress / Concurrency Tests for Build Cancellation** - *Not Started*
   - Simulate two concurrent builds; cancel one; verify isolation of `build_cancel_event` and proper cleanup.

73. **Integrate Coverage Threshold in CI** - *Not Started*
   - Run `pytest --cov` in CI; fail or warn on significant coverage drops; generate an HTML coverage report.

75. **Edge-Case Error-Path Tests** - *Not Started*
   - Add tests simulating disk-full (`OSError(ENOSPC)`), log-write permission errors, JSON decode failures, etc., to ensure graceful error handling. 
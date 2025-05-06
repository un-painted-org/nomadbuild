# Web UI Testing

This document describes the testing approach for the NomadBuild Web UI, including API endpoints and Socket.IO events.

## Overview

The Web UI testing suite consists of three main components:

1. **API Endpoint Tests**: Tests for the RESTful API endpoints exposed by the Web UI server.
2. **Socket.IO Event Tests**: Tests for the real-time Socket.IO events used for build status updates and other communications.
3. **Build Flow Tests**: End-to-end tests for the complete build flow from request to completion.

## Test Structure

The Web UI tests are organized into the following files:

- `src/tests/test_web_ui_endpoints.py`: Tests for the RESTful API endpoints.
- `src/tests/test_web_ui_socketio.py`: Tests for the Socket.IO events.
- `src/tests/test_web_ui_build_flow.py`: Tests for the complete build flow.
- `src/tests/test_web_ui.py`: General tests for the Web UI module.
- `src/tests/test_ui_cancellation.py`: Tests for build cancellation functionality.

## Running the Tests

### Using Docker (Recommended)

To run all Web UI tests using Docker:

```bash
./nomadbuild.sh --test --web-ui
```

To run a specific test file:

```bash
./nomadbuild.sh --test --path src/tests/test_web_ui_endpoints.py
```

### Running Natively (Not Recommended)

While it's possible to run the tests natively, it's not recommended as the tests are designed to run in the Docker container environment. If you still want to run them natively:

1. Install the required dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Run the tests:
   ```bash
   python -m pytest src/tests/test_web_ui_endpoints.py
   ```

## Test Fixtures

The tests use several fixtures defined in `src/tests/conftest.py`:

- `flask_app`: Creates a Flask test client for testing API endpoints.
- `socketio_app`: Creates a Flask-SocketIO test client for testing Socket.IO events.
- `mock_builder`: Creates a mock builder for testing.
- `mock_socketio`: Creates a mock SocketIO for testing.
- `mock_request_context`: Creates a mock Flask request context.

## API Endpoint Tests

The API endpoint tests in `test_web_ui_endpoints.py` cover the following endpoints:

- `/api/build`: Tests for initiating a build with a specific tag.
- `/api/tags`: Tests for retrieving available tags.
- `/api/status`: Tests for checking the server status.
- `/api/last_build`: Tests for retrieving information about the last build.

## Socket.IO Event Tests

The Socket.IO event tests in `test_web_ui_socketio.py` cover the following events:

- `ping/pong`: Tests for basic connectivity.
- `get_tags`: Tests for retrieving available tags.
- `check_build_status`: Tests for checking the current build status.
- `cancel_build`: Tests for cancelling an active build.
- `get_last_build`: Tests for retrieving information about the last build.

## Build Flow Tests

The build flow tests in `test_web_ui_build_flow.py` cover the complete build process:

- **Success Flow**: Tests the flow from build request to successful completion.
- **Failure Flow**: Tests the flow from build request to failure.
- **Cancellation Flow**: Tests the flow from build request to cancellation.

## Test Mocking

The tests use extensive mocking to isolate the Web UI code from its dependencies:

- `builder_build`: Mocked to simulate the build process.
- `socketio`: Mocked to capture emitted events.
- `threading.Thread`: Mocked to control thread execution.
- `ensure_clean_repo_for_build`: Mocked to bypass Git operations.

## Adding New Tests

When adding new tests for the Web UI:

1. Determine which test file is most appropriate for your test.
2. Use the existing fixtures and mocking patterns.
3. Ensure your test runs in the Docker container environment.
4. Make sure your test is isolated from other tests.
5. Add appropriate assertions to verify the expected behavior.

## Common Issues

- **Flask Context Errors**: Many Flask-related tests require a proper application context. Use the `flask_app` fixture to ensure this.
- **Socket.IO Connection Issues**: Socket.IO tests may fail if the Socket.IO server is not properly mocked. Use the `socketio_app` fixture.
- **Thread Safety**: Be careful when testing code that uses threads. Use proper mocking and cleanup to avoid test interference.

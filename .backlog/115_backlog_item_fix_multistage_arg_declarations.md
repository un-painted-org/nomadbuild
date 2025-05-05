# Backlog Item 115: Fix Multi-Stage Build ARG Declarations

## Description

This backlog item focuses on fixing the ARG declarations in multi-stage builds to follow Docker best practices. Currently, the Dockerfile template has issues with ARG scoping in multi-stage builds, which could lead to build failures or unexpected behavior.

## Requirements

1. Fix ARG declarations in multi-stage builds to follow Docker best practices
2. Move global ARGs before the first FROM instruction
3. Re-declare ARGs after each new FROM instruction
4. Add documentation about ARG scoping in multi-stage builds
5. Update verification tests to check ARG declarations

## Implementation Details

### Current Issues

The current Dockerfile template has the following issues with ARG declarations:

```dockerfile
# Start a new stage for the runtime image
# Re-declare ARG for the new stage
ARG BASE_IMAGE_DIGEST
FROM espressif/idf@${BASE_IMAGE_DIGEST} AS runtime
```

According to Docker best practices, ARGs that are used in FROM instructions must be declared *before* the first FROM. Then they need to be redeclared after each new FROM if they'll be used in that stage.

### Proposed Solution

1. **Move Global ARGs**: All ARGs that are used in FROM instructions should be declared before the first FROM instruction.

```dockerfile
ARG BASE_IMAGE_DIGEST
FROM espressif/idf@${BASE_IMAGE_DIGEST} AS builder
```

2. **Re-declare ARGs**: ARGs need to be redeclared after each new FROM instruction if they'll be used in that stage.

```dockerfile
FROM espressif/idf@${BASE_IMAGE_DIGEST} AS runtime
ARG BASE_IMAGE_DIGEST
ARG TZ
ARG LC_ALL
ARG LANG
ARG PYTHONHASHSEED
# ... other ARGs needed in this stage
```

3. **Add Documentation**: Add comments in the Dockerfile template explaining ARG scoping in multi-stage builds.

```dockerfile
# ARG values are not persisted across stages in multi-stage builds
# ARGs used in FROM instructions must be declared before the first FROM
# ARGs must be redeclared after each new FROM if they'll be used in that stage
```

4. **Update Verification Tests**: Add tests to verify that ARG declarations follow best practices.

```python
def test_arg_declarations():
    """Test that ARG declarations follow best practices."""
    # Check that ARGs used in FROM are declared before the first FROM
    # Check that ARGs are redeclared after each new FROM if used in that stage
```

## Testing

The changes should be tested by:

1. Building the Docker image with the fixed ARG declarations
2. Verifying that all ARGs are correctly passed to each stage
3. Running the verification tests to check ARG declarations
4. Testing with different ARG values to ensure they're correctly used in each stage

## Acceptance Criteria

- All ARGs used in FROM instructions are declared before the first FROM
- ARGs are redeclared after each new FROM if used in that stage
- Documentation about ARG scoping is added to the Dockerfile template
- Verification tests check ARG declarations
- The Docker image builds successfully with the fixed ARG declarations

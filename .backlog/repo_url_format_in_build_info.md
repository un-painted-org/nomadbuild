# 131. Repository URL Format in build_info.json

## Issue Description

The `build_info.json` file needs to be updated to use a new format for repository URL information. Currently, the format is not consistent and does not work for both custom and default repositories. We don't care about backward compatibility

We need to transition to a new format that works for both custom and default repositories:

For custom repositories:
```json
"repo_url": {
    "custom": true,
    "url": "https://github.com/marsmensch/ESP-Miner.git"
}
```

For default repositories:
```json
"repo_url": {
    "custom": false,
    "url": "https://github.com/bitaxeorg/ESP-Miner"
}
```

## Current Status

1. **What works:**
   - For custom repositories (when using `NOMADBUILD_ESP_MINER_REPO_URL`), a `custom_repo` field is added to the `build_info.json` file with `"used": true` and the custom URL.

2. **What doesn't work:**
   - The consistent implementation of the `repo_url` field is missing from the `build_info.json` file for both default and custom repositories.
   - The code in `utils.py` appears to be adding the `repo_url` field to the `build_info` dictionary, but it's not being saved to the file.
   - We need test cases to ensure the new format is correctly implemented according to the issue description and replace all code using the `custom_repo` url field.


## Implementation Approach

The implementation in `utils.py` has the following logic:

```python
# Add repo_url field with the new format
build_info['repo_url'] = {
    'custom': bool(is_custom_repo),
    'url': custom_repo_url if is_custom_repo else ESP_MINER_REPO
}

# For backward compatibility, also include the custom_repo field if using a custom repo
if is_custom_repo and custom_repo_url:
    build_info['custom_repo'] = {
        'used': True,
        'url': custom_repo_url
    }
```

Apparently, the validation code checks for the presence of the `repo_url` field and raises an error if it's missing, but somehow the field is not being saved to the file.

## Proposed Solution

1. Debug the `create_and_save_build_info` function to understand why the `repo_url` field is not being saved to the file.
2. Ensure that the `repo_url` field is ALWAYS correctly added to the `build_info.json` file for both default and custom repositories.
3. Update the test case to match the expected behavior.

## Next Steps

1. Add logging statements to track the content of the `build_info` dictionary before and after it's saved to the file.
2. Check if there's any code that might be modifying the dictionary before it's saved.
3. Verify that the JSON serialization is working correctly.

## Acceptance Criteria

1. For custom repositories, the `build_info.json` file should contain the new `repo_url` field.
2. For default repositories, the `build_info.json` file should contain the new `repo_url` field.
3. All tests should pass with the updated implementation for both custom and default repositories.

## Priority

HIGH - This is important for reproducibility and tracking the source of firmware builds.

## Estimated Effort

Small - The code changes should be minimal, but debugging might take some time.

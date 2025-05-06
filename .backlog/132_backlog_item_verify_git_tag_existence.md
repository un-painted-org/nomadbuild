# Backlog Item 132: Verify Git Tag Existence Before Checkout

## Description

Currently, when a user supplies a git tag (e.g., via `--tag v2.7.0`), the system attempts to check out that tag without first verifying if it exists. If the tag doesn't exist, this can lead to confusing error messages and a poor user experience. This backlog item aims to add validation to check if a user-supplied git tag exists before attempting to check it out.

## Problem Statement

When a user provides a non-existent tag, the current behavior is to attempt a checkout, which fails with git-specific error messages that might not be clear to all users. This can happen in several scenarios:
- User makes a typo in the tag name
- User specifies a tag that exists in one repository but not in another
- User specifies a tag that was deleted or renamed
- User specifies a tag format that doesn't match the repository's tagging scheme

## Requirements

1. **Tag Validation**:
   - Before attempting to check out a tag, verify that it exists in the repository
   - Implement this validation for both the default ESP-Miner repository and custom repositories
   - Ensure the validation is efficient and doesn't significantly impact performance

2. **Error Handling**:
   - Provide clear, user-friendly error messages when a tag doesn't exist
   - Include suggestions for how to resolve the issue (e.g., list available tags)
   - Ensure error messages are consistent with the rest of the application

3. **Tag Listing**:
   - Add support for listing available tags to help users select valid tags
   - Consider adding a `--list-tags` option to show available tags
   - Format the tag list in a user-friendly way

4. **Documentation**:
   - Update documentation to explain the tag validation behavior
   - Include examples of valid and invalid tag usage
   - Document the new tag listing feature

5. **Testing**:
   - Add comprehensive tests for the tag validation logic
   - Include tests for both valid and invalid tags
   - Test with both default and custom repositories

## Acceptance Criteria

- [ ] When a user supplies a non-existent tag, the system provides a clear error message before attempting checkout
- [ ] The error message includes helpful information about why the tag is invalid
- [ ] The system provides a way to list available tags
- [ ] Documentation is updated to explain the tag validation behavior
- [ ] Comprehensive tests are added for the tag validation logic
- [ ] The validation works for both default and custom repositories

## Implementation Notes

### Possible Implementation Approach

1. Use `git ls-remote --tags <repository-url>` to get a list of available tags
2. Check if the user-supplied tag exists in this list
3. If the tag exists, proceed with checkout
4. If the tag doesn't exist, provide a clear error message and suggest alternatives

### Code Areas to Modify

- `src/builder/git_ops.py`: Add tag validation logic
- `src/builder/cli.py`: Update argument parsing to handle tag validation
- `src/builder/utils.py`: Add helper functions for tag listing and validation

### Potential Challenges

- Handling network issues when fetching tags from remote repositories
- Balancing performance with validation thoroughness
- Ensuring consistent behavior across different git versions and platforms

## Related Items

- This is related to the reproducibility features that rely on specific tags
- This would enhance the user experience for the `--tag` option

## Priority

Medium-High: This is an important usability improvement that prevents confusing errors.

## Estimated Effort

Medium: Requires changes to git operations logic and error handling, but the scope is well-defined.

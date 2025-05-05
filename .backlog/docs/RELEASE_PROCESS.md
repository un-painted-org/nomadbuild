# Release Process

This document describes how to create and publish a new release of NomadBuild using the `generate_release.sh` script.

## Prerequisites

Before creating a release, ensure that:

1. You are on the `main` branch and it contains all the changes you want to include in the release.
2. All changes have been committed.
3. All tests are passing.
4. You have permission to push to the repository.

## Creating a New Release

### Step 1: Ensure your local repository is up to date

```bash
# Switch to the main branch
git checkout main

# Pull the latest changes
git pull origin main

# Verify that all tests pass
./scripts/test.sh
```

### Step 2: Run the release script

The `generate_release.sh` script automates the release process, including:
- Creating a changelog entry
- Generating release notes
- Updating version references in the codebase
- Creating a Git tag

You can run the script in one of the following ways:

#### Option 1: Let the script calculate the next version automatically

```bash
# For a patch release (e.g., 1.0.0 -> 1.0.1)
./backlog/generate_release.sh --type patch

# For a minor release (e.g., 1.0.0 -> 1.1.0)
./backlog/generate_release.sh --type minor

# For a major release (e.g., 1.0.0 -> 2.0.0)
./backlog/generate_release.sh --type major
```

#### Option 2: Specify the version explicitly

```bash
./backlog/generate_release.sh --version 1.2.3
```

### Step 3: Edit the changelog entry

The script will open your default text editor with a template for the changelog entry. Fill in the details of what has changed in this release:

- **Added**: New features or capabilities
- **Changed**: Changes to existing functionality
- **Deprecated**: Features that will be removed in upcoming releases
- **Removed**: Features that were removed in this release
- **Fixed**: Bug fixes
- **Security**: Security-related changes or improvements

Save and close the editor when you're done.

### Step 4: Edit the release notes

After creating the changelog entry, the script will open your default text editor again with a template for the release notes. The template will be pre-filled with information from the changelog entry, but you can add more details or make changes as needed.

Save and close the editor when you're done.

### Step 5: Commit the changes

The script will update the changelog and version references in the codebase, but it won't commit these changes automatically. You need to commit them manually:

```bash
# Add the changed files
git add CHANGELOG.md
git add RELEASE_NOTES_*.md
git add <any other files that were updated>

# Commit the changes
git commit -m "Release v1.2.3"
```

### Step 6: Push the changes and tag to GitHub

```bash
# Push the commit
git push origin main

# Push the tag
git push origin v1.2.3
```

### Step 7: Create a GitHub release

1. Go to the repository on GitHub
2. Click on "Releases" in the right sidebar
3. Click on "Draft a new release"
4. Select the tag you just pushed
5. Set the release title to "Release v1.2.3"
6. Copy and paste the content from the `RELEASE_NOTES_1.2.3.md` file into the description
7. Click "Publish release"

## Testing the Release Process

If you want to test the release process without making any changes, you can use the `--dry-run` option:

```bash
./backlog/generate_release.sh --dry-run
```

This will show you what would happen without actually making any changes.

## Troubleshooting

### The script can't determine the current version

If the script can't determine the current version from the CHANGELOG.md file, it will default to 0.0.0. You can specify the version explicitly using the `--version` option.

### The editor doesn't open

The script uses the `$EDITOR` environment variable to determine which editor to use. If this variable is not set, it defaults to `vi`. You can set the `$EDITOR` environment variable to your preferred editor:

```bash
export EDITOR=nano
```

### The script fails to update version references

The script attempts to update version references in common files like package.json, setup.py, and config.yaml. If your project uses different files for version references, you may need to update them manually or modify the script.

## Example Workflow

Here's an example of a complete release workflow:

```bash
# Ensure you're on the main branch with the latest changes
git checkout main
git pull origin main

# Run the tests to make sure everything is working
./scripts/test.sh

# Create a new patch release
./backlog/generate_release.sh --type patch

# Edit the changelog entry and release notes in your editor

# Commit the changes
git add CHANGELOG.md RELEASE_NOTES_*.md
git commit -m "Release v1.0.1"

# Push the changes and tag
git push origin main
git push origin v1.0.1

# Create a GitHub release through the web interface
```

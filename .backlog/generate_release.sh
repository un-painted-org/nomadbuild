#!/bin/bash
# generate_release.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Script to generate a new release with formatted changelog entries

set -e

# Default values
VERSION=""
TYPE="patch"
DRY_RUN=false
CHANGELOG_FILE="CHANGELOG.md"
RELEASE_TEMPLATE=".github/RELEASE_TEMPLATE.md"
TEMP_CHANGELOG="/tmp/changelog_entry.md"

# Function to display usage information
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -v, --version VERSION   Specify the version number (e.g., 1.0.0)"
    echo "  -t, --type TYPE         Specify the release type: major, minor, patch (default: patch)"
    echo "  -d, --dry-run           Show what would be done without making changes"
    echo "  -h, --help              Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --version 1.0.0"
    echo "  $0 --type minor"
    echo "  $0 --dry-run"
    exit 1
}

# Function to validate semantic version
validate_version() {
    if ! [[ $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "Error: Version must be in the format X.Y.Z (e.g., 1.0.0)"
        exit 1
    fi
}

# Function to calculate next version based on current version and type
calculate_next_version() {
    local current_version=$1
    local release_type=$2
    
    IFS='.' read -r major minor patch <<< "$current_version"
    
    case $release_type in
        major)
            echo "$((major + 1)).0.0"
            ;;
        minor)
            echo "$major.$((minor + 1)).0"
            ;;
        patch)
            echo "$major.$minor.$((patch + 1))"
            ;;
        *)
            echo "Error: Invalid release type. Must be major, minor, or patch."
            exit 1
            ;;
    esac
}

# Function to get the current version from CHANGELOG.md
get_current_version() {
    if [ ! -f "$CHANGELOG_FILE" ]; then
        echo "0.0.0"
        return
    fi
    
    # Extract the latest version from CHANGELOG.md
    local version=$(grep -E '^\#\# \[[0-9]+\.[0-9]+\.[0-9]+\]' "$CHANGELOG_FILE" | head -1 | sed -E 's/^\#\# \[([0-9]+\.[0-9]+\.[0-9]+)\].*/\1/')
    
    if [ -z "$version" ]; then
        echo "0.0.0"
    else
        echo "$version"
    fi
}

# Function to create a new changelog entry
create_changelog_entry() {
    local version=$1
    local date=$(date +"%Y-%m-%d")
    
    # Create a temporary file for the changelog entry
    cat > "$TEMP_CHANGELOG" << EOF
## [$version] - $date

### Added
- 

### Changed
- 

### Deprecated
- 

### Removed
- 

### Fixed
- 

### Security
- 

EOF
    
    # Open the temporary file in the default editor
    ${EDITOR:-vi} "$TEMP_CHANGELOG"
    
    # Check if the file was modified
    if [ ! -s "$TEMP_CHANGELOG" ]; then
        echo "Error: Changelog entry is empty. Aborting."
        rm "$TEMP_CHANGELOG"
        exit 1
    fi
    
    # Insert the new changelog entry after the Unreleased section
    if [ -f "$CHANGELOG_FILE" ]; then
        sed -i.bak '/## \[Unreleased\]/,/^$/{/^$/!{/## \[Unreleased\]/!d}}' "$CHANGELOG_FILE"
        sed -i.bak "/## \[Unreleased\]/a\\
\\
$(cat "$TEMP_CHANGELOG")" "$CHANGELOG_FILE"
        rm "$CHANGELOG_FILE.bak"
    else
        echo "Error: $CHANGELOG_FILE not found."
        exit 1
    fi
    
    rm "$TEMP_CHANGELOG"
}

# Function to create a release template
create_release_template() {
    local version=$1
    local release_file="RELEASE_NOTES_$version.md"
    
    # Copy the release template
    if [ -f "$RELEASE_TEMPLATE" ]; then
        cp "$RELEASE_TEMPLATE" "$release_file"
        sed -i.bak "s/{version}/$version/g" "$release_file"
        rm "$release_file.bak"
        
        # Extract changelog entry for this version
        local changelog_content=$(sed -n "/## \[$version\]/,/## \[/p" "$CHANGELOG_FILE" | sed '$d')
        
        # Replace placeholders in the release template with changelog content
        if [[ "$changelog_content" == *"### Added"* ]]; then
            added_content=$(echo "$changelog_content" | sed -n '/### Added/,/### /p' | sed '1d;$d')
            sed -i.bak "s/<!-- List the new features or enhancements in this release -->/$(echo "$added_content" | sed 's/\//\\\//g')/g" "$release_file"
            rm "$release_file.bak"
        fi
        
        if [[ "$changelog_content" == *"### Fixed"* ]]; then
            fixed_content=$(echo "$changelog_content" | sed -n '/### Fixed/,/### /p' | sed '1d;$d')
            sed -i.bak "s/<!-- List the bugs that were fixed in this release -->/$(echo "$fixed_content" | sed 's/\//\\\//g')/g" "$release_file"
            rm "$release_file.bak"
        fi
        
        if [[ "$changelog_content" == *"### Breaking Changes"* ]]; then
            breaking_content=$(echo "$changelog_content" | sed -n '/### Breaking Changes/,/### /p' | sed '1d;$d')
            sed -i.bak "s/<!-- List any breaking changes that users should be aware of -->/$(echo "$breaking_content" | sed 's/\//\\\//g')/g" "$release_file"
            rm "$release_file.bak"
        fi
        
        if [[ "$changelog_content" == *"### Deprecated"* ]]; then
            deprecated_content=$(echo "$changelog_content" | sed -n '/### Deprecated/,/### /p' | sed '1d;$d')
            sed -i.bak "s/<!-- List any deprecated features that will be removed in future releases -->/$(echo "$deprecated_content" | sed 's/\//\\\//g')/g" "$release_file"
            rm "$release_file.bak"
        fi
        
        if [[ "$changelog_content" == *"### Security"* ]]; then
            security_content=$(echo "$changelog_content" | sed -n '/### Security/,/### /p' | sed '1d;$d')
            sed -i.bak "s/<!-- List any security-related updates -->/$(echo "$security_content" | sed 's/\//\\\//g')/g" "$release_file"
            rm "$release_file.bak"
        fi
        
        # Open the release file in the default editor
        ${EDITOR:-vi} "$release_file"
        
        echo "Release notes created at $release_file"
    else
        echo "Error: Release template not found at $RELEASE_TEMPLATE"
        exit 1
    fi
}

# Function to update version references in the codebase
update_version_references() {
    local version=$1
    
    echo "Updating version references in the codebase..."
    
    # Update version in package.json if it exists
    if [ -f "package.json" ]; then
        sed -i.bak "s/\"version\": \"[0-9]*\.[0-9]*\.[0-9]*\"/\"version\": \"$version\"/" "package.json"
        rm "package.json.bak"
        echo "Updated version in package.json"
    fi
    
    # Update version in setup.py if it exists
    if [ -f "setup.py" ]; then
        sed -i.bak "s/version='[0-9]*\.[0-9]*\.[0-9]*'/version='$version'/" "setup.py"
        rm "setup.py.bak"
        echo "Updated version in setup.py"
    fi
    
    # Update version in config.yaml if it exists
    if [ -f "config.yaml" ]; then
        sed -i.bak "s/version: [0-9]*\.[0-9]*\.[0-9]*/version: $version/" "config.yaml"
        rm "config.yaml.bak"
        echo "Updated version in config.yaml"
    fi
}

# Function to create a Git tag
create_git_tag() {
    local version=$1
    local release_file=$2
    
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY RUN] Would create Git tag v$version"
        return
    fi
    
    echo "Creating Git tag v$version..."
    
    # Create an annotated tag with the release notes
    if [ -f "$release_file" ]; then
        git tag -a "v$version" -F "$release_file"
    else
        git tag -a "v$version" -m "Release v$version"
    fi
    
    echo "Git tag v$version created"
    echo "To push the tag to the remote repository, run:"
    echo "  git push origin v$version"
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -t|--type)
            TYPE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Error: Unknown option $1"
            usage
            ;;
    esac
done

# Get the current version
CURRENT_VERSION=$(get_current_version)
echo "Current version: $CURRENT_VERSION"

# Calculate the next version if not specified
if [ -z "$VERSION" ]; then
    VERSION=$(calculate_next_version "$CURRENT_VERSION" "$TYPE")
    echo "Calculated next $TYPE version: $VERSION"
else
    validate_version "$VERSION"
    echo "Using specified version: $VERSION"
fi

# Confirm with the user
if [ "$DRY_RUN" = false ]; then
    read -p "Create release $VERSION? [y/N] " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# Create a new changelog entry
if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would create changelog entry for version $VERSION"
else
    echo "Creating changelog entry for version $VERSION..."
    create_changelog_entry "$VERSION"
    echo "Changelog entry created"
fi

# Create a release template
if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would create release notes for version $VERSION"
    RELEASE_FILE=""
else
    echo "Creating release notes for version $VERSION..."
    create_release_template "$VERSION"
    RELEASE_FILE="RELEASE_NOTES_$VERSION.md"
fi

# Update version references in the codebase
if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would update version references in the codebase"
else
    update_version_references "$VERSION"
fi

# Create a Git tag
create_git_tag "$VERSION" "$RELEASE_FILE"

echo "Release $VERSION generated successfully!"
if [ "$DRY_RUN" = false ]; then
    echo "Don't forget to commit the changes and push the tag to the remote repository."
fi

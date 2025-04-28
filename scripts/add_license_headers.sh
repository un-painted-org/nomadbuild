#!/usr/bin/env bash
# add_license_headers.sh – One-off helper to prepend MIT headers to all tracked source files.
# Safe to re-run; skips files already containing SPDX marker in first 5 lines.

set -euo pipefail
YEAR=2025
AUTHOR="marsmensch"

append_header() {
  local file="$1"
  local ext="${file##*.}"
  local fname="$(basename "$file")"

  # Skip if header already exists
  if head -5 "$file" | grep -q "SPDX-License-Identifier: MIT"; then return; fi

  case "$ext" in
    sh|py)
      # Preserve shebang if present
      if head -1 "$file" | grep -q "^#!"; then
        local shebang; shebang="$(head -1 "$file")"
        tail -n +2 "$file" > "$file.body"
        { echo "$shebang"; printf "# %s\n# Copyright (c) %s %s\n# SPDX-License-Identifier: MIT\n#\n" "$fname" "$YEAR" "$AUTHOR"; cat "$file.body"; } > "$file.new"
        mv "$file.new" "$file" && rm "$file.body"
      else
        { printf "# %s\n# Copyright (c) %s %s\n# SPDX-License-Identifier: MIT\n#\n" "$fname" "$YEAR" "$AUTHOR"; cat "$file"; } > "$file.new" && mv "$file.new" "$file"
      fi
      ;;
    js|css)
      { printf "/* %s\n * Copyright (c) %s %s\n * SPDX-License-Identifier: MIT\n */\n" "$fname" "$YEAR" "$AUTHOR"; cat "$file"; } > "$file.new" && mv "$file.new" "$file" ;;
    html)
      local first_line; first_line="$(head -1 "$file")"
      if echo "$first_line" | grep -iq "<!doctype"; then
        tail -n +2 "$file" > "$file.body"
        { echo "$first_line"; printf "<!-- %s - Copyright (c) %s %s. SPDX-License-Identifier: MIT -->\n" "$fname" "$YEAR" "$AUTHOR"; cat "$file.body"; } > "$file.new"
        mv "$file.new" "$file" && rm "$file.body"
      else
        { printf "<!-- %s - Copyright (c) %s %s. SPDX-License-Identifier: MIT -->\n" "$fname" "$YEAR" "$AUTHOR"; cat "$file"; } > "$file.new" && mv "$file.new" "$file"
      fi
      ;;
    *)
      return ;;
  esac
}

# Iterate over tracked files with specified extensions
for f in $(git ls-files '*.sh' '*.py' '*.js' '*.css' '*.html'); do
  append_header "$f"
done

echo "Header insertion complete." 
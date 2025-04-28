#!/bin/bash
# download_vendors.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Download vendor JavaScript libraries for NomadBuild

set -e

VENDORS_JS_DIR="src/web_static/vendor/js"
FONTS_DIR="src/web_static/fonts"
ATTRIBUTION_FILE="$VENDORS_JS_DIR/ATTRIBUTION.md"

# Create directories if they don't exist
mkdir -p "$VENDORS_JS_DIR"
mkdir -p "$FONTS_DIR"

# Set library versions
SOCKETIO_VERSION="4.7.4"
QRCODE_VERSION="1.0.0"
HTML5_QRCODE_VERSION="2.3.8"

# Download vendor JavaScript libraries
echo "Downloading vendor JavaScript libraries..."

# Socket.IO
echo "  - Socket.IO v$SOCKETIO_VERSION..."
curl -s -L -o "$VENDORS_JS_DIR/socket.io.min.js" "https://cdn.socket.io/4.7.4/socket.io.min.js"

# QRCode.js
echo "  - QRCode.js v$QRCODE_VERSION..."
curl -s -L -o "$VENDORS_JS_DIR/qrcode.min.js" "https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"

# HTML5-QRCode
echo "  - HTML5-QRCode v$HTML5_QRCODE_VERSION..."
curl -s -L -o "$VENDORS_JS_DIR/html5-qrcode.min.js" "https://unpkg.com/html5-qrcode@$HTML5_QRCODE_VERSION/html5-qrcode.min.js"

# Download Inter font files
echo "Downloading Inter font files (TTF)..."
FONT_BASE_URL="https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_nVMrMxCp50SjIw2boKoduKmMEV"

echo "  - Weight 400 (Regular)..."
curl -s -L -o "$FONTS_DIR/inter-regular.ttf" "${FONT_BASE_URL}uLyfMZg.ttf"
echo "  - Weight 500 (Medium)..."
curl -s -L -o "$FONTS_DIR/inter-medium.ttf" "${FONT_BASE_URL}uI6fMZg.ttf"
echo "  - Weight 600 (SemiBold)..."
curl -s -L -o "$FONTS_DIR/inter-semibold.ttf" "${FONT_BASE_URL}uGKYMZg.ttf"
echo "  - Weight 700 (Bold)..."
curl -s -L -o "$FONTS_DIR/inter-bold.ttf" "${FONT_BASE_URL}uFuYMZg.ttf"

# Create attribution file
echo "Creating attribution file..."
# Add Bitaxe Project Attribution first
echo "## Bitaxe Project" > "$ATTRIBUTION_FILE"
echo "- ESP-Miner Repository: [https://github.com/bitaxeorg/ESP-Miner](https://github.com/bitaxeorg/ESP-Miner)" >> "$ATTRIBUTION_FILE"
echo "- Website: [https://bitaxe.org/](https://bitaxe.org/)" >> "$ATTRIBUTION_FILE"
echo "- License: GPL-3.0" >> "$ATTRIBUTION_FILE"
echo "- Description: Bitaxe is an open-source Bitcoin ASIC miner for the ESP32. The ESP-Miner firmware powers Bitaxe hardware devices." >> "$ATTRIBUTION_FILE"
echo "" >> "$ATTRIBUTION_FILE" # Add a newline

# Append other library details
cat >> "$ATTRIBUTION_FILE" << EOL
## Socket.IO (v$SOCKETIO_VERSION)
- Source: [socket.io](https://socket.io/)
- Repository: [GitHub](https://github.com/socketio/socket.io)
- License: MIT
- Description: Socket.IO enables real-time, bidirectional and event-based communication between the browser and the server.

## QRCode.js (v$QRCODE_VERSION)
- Source: [QRCode.js](https://davidshimjs.github.io/qrcodejs/)
- Repository: [GitHub](https://github.com/davidshimjs/qrcodejs)
- License: MIT
- Description: QRCode.js is a cross-browser QRCode generator for JavaScript.

## HTML5-QRCode (v$HTML5_QRCODE_VERSION)
- Source: [scanapp.org](https://scanapp.org/)
- Repository: [GitHub](https://github.com/mebjas/html5-qrcode)
- License: Apache-2.0
- Description: HTML5 QR code scanner library that can be embedded in websites for QR code scanning.
EOL

echo "Vendor libraries have been downloaded to $VENDORS_JS_DIR"
echo "Attribution information has been saved to $ATTRIBUTION_FILE"

# Convert ATTRIBUTION.md to HTML and inject into template
TEMPLATE_FILE="src/web_templates/index.html.template"
OUTPUT_FILE="src/web_templates/index.html"
TMP_HTML="/tmp/attributions.html"
PLACEHOLDER="%%ATTRIBUTIONS_HTML%%"

echo "Converting attributions to HTML using pandoc..."
if command -v pandoc &> /dev/null; then
    if pandoc "$ATTRIBUTION_FILE" -f markdown -t html -o "$TMP_HTML"; then
        echo "Pandoc conversion successful."
        
        # Modify pandoc output to match original CSS structure
        echo "Adjusting generated HTML structure..."
        sed -i 's/<h2>/<h4>/g' "$TMP_HTML"
        sed -i 's#<\/h2>#<\/h4>#g' "$TMP_HTML"
        sed -i 's/<ul>/<ul class="attribution-details">/g' "$TMP_HTML"
        
        # Read MODIFIED HTML content
        ATTRIBUTION_HTML=$(<"$TMP_HTML")
        
        # Use perl for robust multiline replacement if available, otherwise fallback to sed
        if command -v perl &> /dev/null; then
            echo "Injecting HTML into template using perl..."
            # Read template and replace placeholder using # as delimiter
            perl -pe 'BEGIN{undef $/; $html=shift} s#'$PLACEHOLDER'#$html#;' "$ATTRIBUTION_HTML" < "$TEMPLATE_FILE" > "$OUTPUT_FILE"
            if [ $? -eq 0 ]; then
                echo "HTML injected successfully into $OUTPUT_FILE"
            else
                echo "ERROR: Perl injection failed. Copying template instead."
                cp "$TEMPLATE_FILE" "$OUTPUT_FILE"
            fi
        else 
            echo "WARNING: perl not found. Attempting injection with sed (might be fragile)..."
            # Sed approach - Use different delimiter # here too for consistency, though less critical
            TEMPLATE_CONTENT=$(<"$TEMPLATE_FILE")
            # Ensure placeholder is treated literally, use # delimiter
            # This sed command is complex and might still fail depending on ATTRIBUTION_HTML content
            # Using printf to handle potential special characters in ATTRIBUTION_HTML
            printf "%s\n" "$TEMPLATE_CONTENT" | sed "s#$PLACEHOLDER#$(printf '%s' "$ATTRIBUTION_HTML" | sed 's/[&/\\]/\\&/g')#g" > "$OUTPUT_FILE"

            echo "HTML injected using sed (verify output) into $OUTPUT_FILE"
        fi
        rm "$TMP_HTML" # Clean up temp file
    else
        echo "ERROR: Pandoc conversion failed. Copying template without dynamic attributions."
        cp "$TEMPLATE_FILE" "$OUTPUT_FILE"
    fi
else
    echo "ERROR: pandoc command not found. Cannot generate dynamic attributions. Copying template instead."
    cp "$TEMPLATE_FILE" "$OUTPUT_FILE"
fi

# Replace template comment with generated file comment
echo "Updating comment in generated file..."

# Create a temporary file with the new comment
TEMP_COMMENT_FILE="/tmp/generated_comment.html"
cat > "$TEMP_COMMENT_FILE" << 'EOL'
<!DOCTYPE html>
<!--
IMPORTANT: This is an auto-generated file from index.html.template.
DO NOT EDIT THIS FILE DIRECTLY! It will be overwritten when download_vendors.sh is run.

To make changes to this file:
1. Edit the template file (index.html.template)
2. Run download_vendors.sh to regenerate this file
-->
<html lang="en">
EOL

# Extract everything after the <html lang="en"> tag
TEMP_CONTENT_FILE="/tmp/content_after_comment.html"
if command -v perl &> /dev/null; then
    # Use perl to extract content starting from the line after <html lang="en">
    perl -ne 'print if ($p && $. > $l); $p=1, $l=$. if /<html lang="en">/' "$OUTPUT_FILE" > "$TEMP_CONTENT_FILE"
else
    # Use grep and tail to extract content after the <html lang="en"> tag
    # Find the line number where <html lang="en"> appears
    HTML_LINE_NUM=$(grep -n "<html lang=\"en\">" "$OUTPUT_FILE" | cut -d: -f1)
    if [ -n "$HTML_LINE_NUM" ]; then
        # Add 1 to get the line after <html lang="en">
        NEXT_LINE=$((HTML_LINE_NUM + 1))
        tail -n +$NEXT_LINE "$OUTPUT_FILE" > "$TEMP_CONTENT_FILE"
    else
        echo "ERROR: Could not find <html lang=\"en\"> tag. Comment replacement failed."
        rm "$TEMP_COMMENT_FILE"
        ls -la "$VENDORS_JS_DIR"
        ls -la "$FONTS_DIR"
        ls -la "src/web_templates/"
        exit 1
    fi
fi

# Combine the new comment and the content
cat "$TEMP_COMMENT_FILE" "$TEMP_CONTENT_FILE" > "$OUTPUT_FILE"

# Clean up temporary files
rm "$TEMP_COMMENT_FILE" "$TEMP_CONTENT_FILE"

# List the files
ls -la "$VENDORS_JS_DIR"
ls -la "$FONTS_DIR"
ls -la "src/web_templates/" 
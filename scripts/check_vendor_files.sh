#!/bin/bash
# check_vendor_files.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Script to check if vendor JavaScript libraries exist and download them if missing

VENDOR_DIR="/app/src/web_static/vendor/js"
ATTRIBUTION_FILE="$VENDOR_DIR/ATTRIBUTION.md"

echo "Checking for vendor JavaScript libraries..."

# Create vendor directory if it doesn't exist
if [ ! -d "$VENDOR_DIR" ]; then
    echo "Vendor directory does not exist. Creating it..."
    mkdir -p "$VENDOR_DIR"
fi

# Check for required files
SOCKET_IO_FILE="$VENDOR_DIR/socket.io.min.js"
QRCODE_FILE="$VENDOR_DIR/qrcode.min.js"
HTML5_QRCODE_FILE="$VENDOR_DIR/html5-qrcode.min.js"

MISSING_FILES=false

if [ ! -f "$SOCKET_IO_FILE" ]; then
    echo "Socket.IO library missing."
    MISSING_FILES=true
fi

if [ ! -f "$QRCODE_FILE" ]; then
    echo "QRCode.js library missing."
    MISSING_FILES=true
fi

if [ ! -f "$HTML5_QRCODE_FILE" ]; then
    echo "HTML5-QRCode library missing."
    MISSING_FILES=true
fi

# Download missing files if needed
if [ "$MISSING_FILES" = true ]; then
    echo "Some vendor files are missing. Downloading them now..."
    
    # Download Socket.IO if missing
    if [ ! -f "$SOCKET_IO_FILE" ]; then
        echo "Downloading Socket.IO v4.7.4..."
        curl -s "https://cdn.socket.io/4.7.4/socket.io.min.js" -o "$SOCKET_IO_FILE"
    fi
    
    # Download QRCode.js if missing
    if [ ! -f "$QRCODE_FILE" ]; then
        echo "Downloading QRCode.js v1.0.0..."
        curl -s "https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js" -o "$QRCODE_FILE"
    fi
    
    # Download HTML5-QRCode if missing
    if [ ! -f "$HTML5_QRCODE_FILE" ]; then
        echo "Downloading HTML5-QRCode v2.3.8..."
        curl -s "https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js" -o "$HTML5_QRCODE_FILE"
    fi
    
    # Create attribution file if missing
    if [ ! -f "$ATTRIBUTION_FILE" ]; then
        echo "Creating attribution file..."
        cat > "$ATTRIBUTION_FILE" << EOF
# Third-Party JavaScript Libraries Attribution

This document lists the third-party JavaScript libraries used in NomadBuild and their respective licenses.

## Socket.IO (v4.7.4)
- **Source:** https://socket.io/
- **License:** MIT
- **Description:** Socket.IO enables real-time, bidirectional and event-based communication between the browser and the server.

## QRCode.js (v1.0.0)
- **Source:** https://github.com/davidshimjs/qrcodejs
- **License:** MIT
- **Description:** QRCode.js is a cross-browser QRCode generator for JavaScript.

## HTML5-QRCode (v2.3.8)
- **Source:** https://github.com/mebjas/html5-qrcode
- **License:** Apache-2.0
- **Description:** HTML5 QR code scanner library that can be embedded in websites for QR code scanning.

## License Texts

### MIT License
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### Apache License 2.0
A copy of the Apache License 2.0 can be found at: https://www.apache.org/licenses/LICENSE-2.0
EOF
    fi
    
    echo "Vendor files download complete!"
else
    echo "All vendor files are present."
fi

echo "Vendor library check completed." 
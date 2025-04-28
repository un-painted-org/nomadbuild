/* main.js
 * Copyright (c) 2025 marsmensch
 * SPDX-License-Identifier: MIT
 */
/**
 * NomadBuild - Web UI 
 * Main JavaScript for client-side functionality
 */

// Error logging for debugging
window.addEventListener('error', function(event) {
    console.error('JavaScript error caught:', event.error, 'at', event.filename, 'line', event.lineno, 'column', event.colno);
});

// Global variables
let socket;
let isConnected = false;
let selectedDeviceIP = null; // Changed from selectedDevice
let selectedTag = null;
let buildInProgress = false;
let buildStartTime = null;
let buildProgress = 0;
let storedBuilds = [];
let serverStatusInterval;
let socketPingInterval;
let lastSuccessfulBuild = null; // Store info of the last successful build

// DOM Elements
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM content loaded event fired');
    // Ensure page initialization happens after a small delay to ensure all elements are loaded
    setTimeout(function() {
        console.log('Initializing page after delay...');
        initializePage();
    }, 500);
});

function initializePage() {
    console.log('Initializing page...');
    
    // Make sure the attribution modal is hidden initially
    const attributionModal = document.getElementById('attribution-modal');
    if (attributionModal) {
        console.log('Ensuring attribution modal is hidden on page load');
        attributionModal.classList.add('hidden');
    } else {
        console.error('Attribution modal not found in DOM');
    }
    
    // Initialize the socket connection
    initializeSocket();
    
    // Set up event listeners
    setupEventListeners();
    
    // Apply dark theme by default
    applyDarkTheme();
    
    // Check if a section is already active, if not, activate the build section
    const activeSection = document.querySelector('.content-section.active');
    if (!activeSection) {
        showSection('build');
    }
    
    // Load stored builds from localStorage (might be deprecated if only last build matters)
    // loadStoredBuilds(); // Consider removing if only last build is used
    
    // Set up interval to check server status
    serverStatusInterval = setInterval(checkServerStatus, 5000);
    
    // Fetch initial last build info
    fetchLastBuildInfo(); 
    
    // Debug log for sections and buttons
    logSectionsAndButtons();
}

function initializeSocket() {
    console.log('Initializing socket connection...');
    
    socket = io({
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        timeout: 10000
    });
    
    // Socket event handlers
    socket.on('connect', function() {
        console.log('Socket connected');
        isConnected = true;
        updateConnectionStatus(true);
        
        // Set up ping interval when connected
        socketPingInterval = setInterval(function() {
            if (isConnected) {
                console.log('Pinging server...');
                const pingTime = Date.now();
                socket.emit('ping', { time: pingTime });
            }
        }, 15000);
        
        // Get initial data
        // refreshDevices(); // Changed to IP input
        fetchTags();
        fetchLastBuildInfo(); // Fetch last build info on connect too
        
        // Update clear log button text on connect
        updateClearButtonText();
    });
    
    socket.on('disconnect', function() {
        console.log('Socket disconnected');
        isConnected = false;
        updateConnectionStatus(false);
        
        // Clear ping interval on disconnect
        if (socketPingInterval) {
            clearInterval(socketPingInterval);
        }
    });
    
    socket.on('build_status', function(data) {
        // Log ALL received statuses
        console.log('Received build_status event:', data.status, data);
        
        // --- ADDED: Log the specific status received ---
        if(data && data.status){
            console.log(`[Build Status Handler] Processing status: ${data.status}`);
        } else {
            console.warn('[Build Status Handler] Received event without status:', data);
            return; // Cannot process without status
        }
        // --- END ADDED LOG ---

        const progressStatusElem = document.getElementById('progress-status');
        const progressMessageElem = document.getElementById('progress-message');
        const buildOutputElem = document.getElementById('build-output');
        let messageHandled = false; // Flag to track if message was used for main status

        if (data.status === 'started') {
            buildInProgress = true;
            // Reset spinner state (remove previous cancelled/completed icons)
            const spinnerElem = document.querySelector('.progress-spinner');
            if (spinnerElem) {
                spinnerElem.classList.remove('cancelled', 'completed');
                spinnerElem.innerHTML = '';
            }
            // Reset status text color to default
            if (progressStatusElem) {
                progressStatusElem.style.color = '';
            }
            // Update heading with the specific tag being built
            if (progressStatusElem && data.tag) {
                progressStatusElem.textContent = `Building Bitaxe firmware ${data.tag}...`;
                // --- Update Output Header Title --- 
                const outputHeaderTitle = document.querySelector('#build-progress .output-header h3');
                if (outputHeaderTitle) {
                    outputHeaderTitle.textContent = `Build Output (${data.tag})`;
                }
                // --- End Update --- 
            } else if (progressStatusElem) {
                progressStatusElem.textContent = 'Building Bitaxe firmware...'; // Fallback
            }
            updateBuildProgress(0, data.message || 'Build started');
            showBuildOutput();
            messageHandled = true; // Message used for main status
            
            // Update the Clear Log button to show "Cancel"
            updateClearButtonText();
            // Hide build complete section if shown previously
            const completeSection = document.getElementById('build-complete');
            if (completeSection) {
                completeSection.classList.add('hidden');
            }
            // Also hide the Flash progress section if visible
            hideFlashProgress(); 
        } else if (data.status === 'progress') {
            const progressMsg = data.message || '';
            let progressValue = data.progress;

            // Update the main status text
            if (progressMessageElem) {
                 progressMessageElem.textContent = progressMsg; 
            }

            // ALSO append the progress message to the output log area
            appendToBuildOutput(progressMsg);
            
            // Always update the progress bar value if provided
            if (typeof progressValue === 'number') {
                buildProgress = progressValue;
                updateBuildProgress(progressValue); 
            }
            // Message is now handled by both status line AND output area
            messageHandled = true;             

        } else if (data.status === 'completed') {
            buildInProgress = false;
            const buildDuration = Math.round((Date.now() - buildStartTime) / 1000);
            updateBuildProgress(100, 'Build completed'); // Update main status
            messageHandled = true;
            
            resetOutputHeaderTitle();
            
            // --- CORRECTLY PROCESS build_info --- 
            const buildInfo = data.build_info;
            console.log('[Build Complete Handler] Received build_info:', buildInfo);
            
            if (!buildInfo) {
                console.error("[Build Complete Handler] Build completed event received, but missing build_info object!");
                appendToBuildOutput("Error: Frontend failed to process build completion data.");
                // Update UI to show failure state
                if (progressStatusElem) {
                    progressStatusElem.textContent = 'Build Post-processing Error';
                    progressStatusElem.style.color = 'var(--color-error)';
                }
                return; // Stop processing this event
            }

            const finalVersion = buildInfo.version || buildInfo.tag || selectedTag || 'unknown';
            const tagUsed = buildInfo.tag || selectedTag || 'unknown';
            console.log(`[Build Complete Handler] Derived finalVersion: ${finalVersion}, tagUsed: ${tagUsed}`);
            
            // Get SHA256 correctly using relative path as key identifier
            let fwSha256 = '';
            const fwRelPath = buildInfo.esp_miner_bin_rel_path;
            if (fwRelPath && buildInfo.sha256_hashes) {
                const fwFilename = fwRelPath.split('/').pop(); // Get filename from relative path
                fwSha256 = buildInfo.sha256_hashes[fwFilename] || '';
                console.log(`[Build Complete Handler] Derived fwSha256: ${fwSha256} (from key ${fwFilename})`);
            } else {
                console.warn('[Build Complete Handler] Could not derive SHA256.', {fwRelPath, hashes: buildInfo.sha256_hashes});
            }
            
            // Store details of this successful build (using correct fields)
            lastSuccessfulBuild = {
                tag: tagUsed,
                timestamp: buildInfo.build_time || new Date().toISOString(),
                duration: buildDuration,
                // Path is implicitly the output dir, relative paths are in buildInfo.files
                firmware_version: finalVersion, 
                output: getBuildOutputText(),
                sha256: fwSha256,
                // Store the whole info object for potential future use
                build_info: buildInfo 
            };
            console.log('[Build Complete Handler] Updated lastSuccessfulBuild:', lastSuccessfulBuild);

            // Explicitly update Flash tab info immediately after build success
            console.log('[Build Complete Handler] Calling updateFlashTabInfo...');
            updateFlashTabInfo(); 
            
            // Show desktop notification
            console.log('[Build Complete Handler] Showing build notification...');
            showBuildNotification('Build Complete', `Firmware build for tag ${finalVersion} completed successfully.`);
            
            // Show the build complete section
            console.log('[Build Complete Handler] Processing build completion UI updates...');
            const completeSection = document.getElementById('build-complete');
            const spinnerElem = document.querySelector('#build-progress .progress-spinner');
            const gotoFlashBtn = document.getElementById('goto-flash');

            if (progressStatusElem) {
                console.log('[Build Complete Handler] Updating progressStatusElem...');
                progressStatusElem.textContent = `Build Complete`;
                progressStatusElem.className = 'success-status'; // Add a class for styling
            } else {
                console.error('[Build Complete Handler] progressStatusElem not found!');
            }
            
            if (spinnerElem) {
                 console.log('[Build Complete Handler] Updating spinnerElem...');
                spinnerElem.classList.add('completed');
                spinnerElem.innerHTML = '<svg viewBox="0 0 24 24" width="36" height="36"><path fill="#4CAF50" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';
            } else {
                console.error('[Build Complete Handler] spinnerElem not found!');
            }
            
            if (completeSection) {
                console.log('[Build Complete Handler] Showing build complete section.');
                const versionElem = completeSection.querySelector('#success-version');
                if (versionElem) {
                     console.log(`[Build Complete Handler] Setting success version text to: ${finalVersion}`);
                     versionElem.textContent = `Version: ${finalVersion}`;
                } else {
                    console.error('[Build Complete Handler] Success version element (#success-version) not found within #build-complete!');
                }

                // Update and show the Go To Flash button
                const gotoFlashBtn = document.getElementById('goto-flash');
                if (gotoFlashBtn) {
                    console.log(`[Build Complete Handler] Updating goto-flash button text to: Flash Version ${finalVersion}`);
                    gotoFlashBtn.textContent = `Flash Version ${finalVersion}`;
                    gotoFlashBtn.disabled = false; // Ensure it's enabled
                } else {
                     console.error('[Build Complete Handler] Go to Flash button (#goto-flash) not found!');
                }
                
                 console.log('[Build Complete Handler] Removing hidden class from completeSection...');
                completeSection.classList.remove('hidden');
            } else {
                console.error('[Build Complete Handler] Build complete section (#build-complete) not found!');
            }
            
            console.log('[Build Complete Handler] Calling updateClearButtonText...');
            // Update the Clear Log button text back to "Clear Log"
            updateClearButtonText();
             console.log('[Build Complete Handler] UI updates finished.');
        } else if (data.status === 'cancelled') {
            // Handle build cancellation
            buildInProgress = false;
            
            // Update progress status to show cancellation
            if (progressStatusElem) {
                progressStatusElem.textContent = 'Build Cancelled';
                progressStatusElem.style.color = 'var(--color-warning)';
            }
            
            // Update progress message
            if (progressMessageElem) {
                progressMessageElem.textContent = data.message || 'Build was cancelled by user';
            }
            
            // Add cancellation notice to build output
            appendToBuildOutput('');
            appendToBuildOutput('*** BUILD CANCELLED BY USER ***');
            appendToBuildOutput(data.message || 'Build process was terminated by user request');
            appendToBuildOutput('');
            
            // Stop the spinner animation
            const spinnerElem = document.querySelector('.progress-spinner');
            if (spinnerElem) {
                spinnerElem.classList.add('cancelled');
                // Add a warning icon to replace the spinner
                spinnerElem.innerHTML = '<svg viewBox="0 0 24 24" width="36" height="36"><path fill="#FFC107" d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>';
            }
            
            // Reset the build-related UI elements
            document.getElementById('build-options').classList.add('hidden');
            
            // Update the Clear Log button text back to "Clear Log"
            updateClearButtonText();
            
            // Re-enable the build button
            const startBuildBtn = document.getElementById('start-build');
            if (startBuildBtn) {
                startBuildBtn.disabled = false;
                
                // Reset the button text to reflect that we can start a new build
                if (selectedTag && selectedTag !== "latest") {
                    startBuildBtn.textContent = `Build Firmware (${selectedTag})`;
                } else {
                    startBuildBtn.textContent = 'Build Latest Stable Firmware';
                }
            }
            
            // Show toast notification about cancellation
            showToast('Build cancelled by user', 'warning');
            
            messageHandled = true;
            hideFlashProgress(); // Also hide flash progress on cancel
        } else if (data.status === 'failed') {
            buildInProgress = false;
            updateBuildProgress(0, 'Build failed'); // Update main status
            messageHandled = true;
            
            // Reset output header title
            resetOutputHeaderTitle();
            
            // Show desktop notification
            showBuildNotification('Build Failed', `Firmware build for tag ${selectedTag} failed. Check output for details.`);
            
            // Enhance failure feedback
            const buildOutput = document.getElementById('build-output');
            const outputContainer = document.querySelector('.output-container'); // Get container
            if (buildOutput) {
                // Add clear error message at the end
                const errorSection = document.createElement('div');
                errorSection.classList.add('build-error-section');
                
                let errorMessage = `
                <div class="error-header">BUILD FAILED</div>
                <div class="error-details">
                    <p>The build process for tag <strong>${selectedTag}</strong> has failed.</p>
                    <p>Possible reasons:</p>
                    <ul>
                        <li>Network connectivity issues</li>
                        <li>Invalid tag selected</li>
                        <li>Missing dependencies</li>
                        <li>Compilation errors</li>
                    </ul>
                    <p>Command that failed: <code>${data.command || 'Build process'}</code></p>
                    <p>Error message: <code>${data.error || 'Unknown error'}</code></p>
                    <p>See the build output above for detailed error messages.</p>
                </div>`;
                
                errorSection.innerHTML = errorMessage;
                buildOutput.appendChild(errorSection);
                
                // Make sure build output is visible and maximized
                if (outputContainer && !outputContainer.classList.contains('maximized')) {
                    console.log('Maximizing output automatically on build failure.');
                    toggleMaximizeOutput(); // <-- CORRECT FUNCTION CALL
                }
                buildOutput.scrollTop = buildOutput.scrollHeight;
            }
            
            // Re-enable the build button
            const startBuildBtn = document.getElementById('start-build');
            if (startBuildBtn) {
                startBuildBtn.disabled = false;
                startBuildBtn.textContent = `Retry Build (${selectedTag})`;
            }
            
            // Append the specific error message from data.error or data.message to output
            appendToBuildOutput(`Error: ${data.error || data.message || 'Unknown build failure'}`);
            
            // Update the Clear Log button text back to "Clear Log"
            updateClearButtonText();
        }
        
        // Append log message if not handled by specific status updates
        if (!messageHandled && data.message) {
            appendToBuildOutput(data.message);
        }
    });
    
    socket.on('flash_status', function(data) {
        console.log('Received flash_status event:', data);
        updateFlashProgress(data);
    });
    
    socket.on('last_build_info', function(data) {
        console.log('Received last_build_info:', data);
        if (data && data.firmware_version) {
            lastSuccessfulBuild = data;
            updateFlashTabInfo();
        } else {
            // Handle case where no last build exists
            lastSuccessfulBuild = null;
            updateFlashTabInfo(); 
        }
    });
    
    socket.on('devices', function(data) {
        console.log('Devices update:', data);
        renderDevices(data.devices);
    });
    
    socket.on('tags', function(data) {
        console.log('Tags update:', data);
        renderTagList(data.tags);
        
        // --- Update Tile Displays ---
        const latestTagDisplay = document.getElementById('latest-tag-display');
        const specificTagsDisplay = document.getElementById('specific-tags-display');

        if (data.tags && data.tags.length > 0) {
            const latestTag = data.tags[0]; // Assuming the first tag is the latest stable
            const topFiveTags = data.tags.slice(0, 5);

            // Update the "Latest Stable" card display
            if (latestTagDisplay) {
                latestTagDisplay.textContent = latestTag;
                console.log(`Updated latest tag display in card: ${latestTag}`);
            } else {
                console.warn('Could not find #latest-tag-display element.');
            }

            // Update the "Specific Version" card display
            if (specificTagsDisplay) {
                // Create a simple list format (e.g., using <br>)
                specificTagsDisplay.innerHTML = topFiveTags.join('<br>'); 
                console.log(`Updated specific tags display in card with: ${topFiveTags.join(', ')}`);
            } else {
                 console.warn('Could not find #specific-tags-display element.');
            }

            // Update the "Latest Stable" card title (redundant but kept for consistency for now)
            // Consider removing this later if the display next to icon is preferred
            const latestBuildCard = document.getElementById('build-latest');
            if (latestBuildCard) {
                const cardTitle = latestBuildCard.querySelector('h3');
                if (cardTitle) {
                    cardTitle.textContent = `Latest Stable`; // Keep original title or adjust as needed
                    // cardTitle.textContent = `Latest Stable (${latestTag})`; // Old logic
                    // console.log(`Updated latest stable card title to include tag: ${latestTag}`);
                }
            } else {
                console.warn('Could not find the #build-latest card to update title.');
            }
        } else {
            console.warn('No tags received or tags array empty, cannot update card displays.');
            if (latestTagDisplay) latestTagDisplay.textContent = 'N/A';
            if (specificTagsDisplay) specificTagsDisplay.textContent = 'N/A';
        }
    });
    
    socket.on('pong', function(data) {
        if (data && data.time) {
            const latency = Date.now() - data.time;
            console.log(`Server ping response: ${latency}ms`);
        }
    });
}

function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Navigation buttons
    const navButtons = document.querySelectorAll('.nav-button');
    navButtons.forEach(button => {
        button.addEventListener('click', function() {
            const sectionId = this.id.replace('nav-', '');
            showSection(sectionId);
        });
    });
    
    // Setup copy address buttons
    setupCopyAddressButtons();
    
    // Setup modal event listeners
    const attributionModal = document.getElementById('attribution-modal');
    const showAttributionBtn = document.getElementById('show-attribution-btn');
    const closeAttributionModalBtn = document.getElementById('close-attribution-modal');
    const closeAttributionBtn = document.getElementById('close-attribution-btn');

    if (attributionModal) {
        console.log('Attribution modal found: yes Is hidden:', attributionModal.classList.contains('hidden'));
        if (showAttributionBtn) {
            console.log('Setting up attribution button click handler');
            showAttributionBtn.addEventListener('click', (e) => {
                e.preventDefault();
                attributionModal.classList.remove('hidden');
            });
        }
        if (closeAttributionModalBtn) {
            console.log('Setting up close modal button handler');
            closeAttributionModalBtn.addEventListener('click', () => {
                attributionModal.classList.add('hidden');
            });
        }
         if (closeAttributionBtn) {
            console.log('Setting up close button handler');
            closeAttributionBtn.addEventListener('click', () => {
                attributionModal.classList.add('hidden');
            });
        }
        
        // Close modal if clicking outside of it
        console.log('Setting up click outside handler for modal');
        window.addEventListener('click', function(event) {
            if (event.target == attributionModal) {
                attributionModal.classList.add('hidden');
            }
        });
    } else {
        console.error('Attribution modal element not found.');
    }

    // Build cards
    const buildLatestCard = document.getElementById('build-latest');
    if (buildLatestCard) {
        console.log('Adding click listener to build-latest card');
        buildLatestCard.addEventListener('click', function() {
            console.log('Build latest card clicked');
            selectedTag = "latest"; // Explicitly set tag indicator for latest build
            showBuildOptions();
        });
    }

    const buildTagCard = document.getElementById('build-tag');
    if (buildTagCard) {
        console.log('Adding click listener to build-tag card');
        buildTagCard.addEventListener('click', function() {
            console.log('Build tag card clicked');
            showTagSelection();
        });
    }

    // Tag selection buttons
    const cancelTagBtn = document.getElementById('cancel-tag');
    if (cancelTagBtn) {
        cancelTagBtn.addEventListener('click', cancelBuild);
    }

    // Build options buttons
    const cancelBuildBtn = document.getElementById('cancel-build');
    if (cancelBuildBtn) {
        cancelBuildBtn.addEventListener('click', cancelBuild);
    }

    const startBuildBtn = document.getElementById('start-build');
    if (startBuildBtn) {
        startBuildBtn.addEventListener('click', function() {
            console.log('Start build button clicked');
            startBuild(); 
        });
    }

    // Build progress controls
    const maximizeOutputBtn = document.getElementById('maximize-output');
    if (maximizeOutputBtn) {
        maximizeOutputBtn.addEventListener('click', toggleMaximizeOutput);
    }

    const copyOutputBtn = document.getElementById('copy-output');
    if (copyOutputBtn) {
        copyOutputBtn.addEventListener('click', copyBuildOutput);
    }

    // Set up clear log button
    const clearLogBtn = document.getElementById('clear-log-btn');
    if (clearLogBtn) {
        clearLogBtn.addEventListener('click', function() {
            if (buildInProgress) {
                // If a build is in progress, show confirmation dialog
                if (confirm("Are you sure you want to cancel the current build?")) {
                    // Cancel the build
                    socket.emit('cancel_build');
                    showToast('Build cancellation requested', 'info');
                }
            } else {
                // If no build is in progress, just clear the log
                clearBuildOutput();
                hideBuildOutput();
                
                // Hide build progress and build complete sections
                const buildProgress = document.getElementById('build-progress');
                const buildComplete = document.getElementById('build-complete');
                
                if (buildProgress) {
                    buildProgress.classList.add('hidden');
                }
                
                if (buildComplete) {
                    buildComplete.classList.add('hidden');
                }
            }
        });
    }

    // Build complete buttons
    const newBuildBtn = document.getElementById('new-build');
    const gotoFlashBtn = document.getElementById('goto-flash');
    
    if (newBuildBtn) {
        newBuildBtn.addEventListener('click', function() {
            // Reset build section UI
            document.getElementById('build-complete').classList.add('hidden');
            document.getElementById('build-progress').classList.add('hidden');
            document.getElementById('build-options').classList.add('hidden');
            document.getElementById('tag-selection').classList.add('hidden');
            document.querySelector('.card-container').classList.remove('hidden'); 
            selectedTag = null; // Reset selected tag
             // Reset spinner appearance
            const spinnerElem = document.querySelector('#build-progress .progress-spinner');
            if (spinnerElem) {
                spinnerElem.classList.remove('completed');
                spinnerElem.innerHTML = ''; // Or restore original spinner SVG/CSS
            }
            // Reset progress status text color/class
            const progressStatusElem = document.getElementById('progress-status');
            if (progressStatusElem) {
                progressStatusElem.className = ''; 
                progressStatusElem.style.color = ''; 
            }
            // Reset output header title
            resetOutputHeaderTitle();
        });
    } else {
        console.error('New Build button not found');
    }

    // --- UPDATED: Go To Flash Button ---
    if (gotoFlashBtn) {
        gotoFlashBtn.addEventListener('click', function() {
            console.log('Go To Flash button clicked');
            showSection('flash');
            // Optionally scroll or highlight the flash section
            // document.getElementById('section-flash').scrollIntoView({ behavior: 'smooth' });
        });
    } else {
        console.error('Go To Flash button (#goto-flash) not found');
    }

    // Flash button listener
    const flashButton = document.getElementById('start-flash');
    if (flashButton) {
        flashButton.addEventListener('click', flashDevice);
    } else {
        console.error('Flash button not found');
    }
    
    // Flash section controls
    // const scanQrBtn = document.getElementById('scan-qr-btn');
    // const closeScannerBtn = document.getElementById('close-scanner');
    // if (scanQrBtn) {
    //     scanQrBtn.addEventListener('click', openQrScanner);
    // }
    // if (closeScannerBtn) {
    //     closeScannerBtn.addEventListener('click', closeQrScanner);
    // }

    // Flash Output Controls
    const copyFlashOutputBtn = document.getElementById('copy-flash-output');
    const clearFlashOutputBtn = document.getElementById('clear-flash-output-btn');
    if (copyFlashOutputBtn) {
        copyFlashOutputBtn.addEventListener('click', copyFlashOutput);
    }
     if (clearFlashOutputBtn) {
        clearFlashOutputBtn.addEventListener('click', clearFlashOutput);
    }

    // IP input listener to enable/disable flash button
    const flashIpInput = document.getElementById('flash-ip');
    if (flashIpInput) {
        flashIpInput.addEventListener('input', function() {
             selectedDeviceIP = this.value.trim();
             updateFlashButtonState(); // Update button based on IP and last build
        });
    }

    console.log('Event listeners set up complete');
}

// Navigation functions
function showSection(sectionId) {
    console.log(`Attempting to show section: ${sectionId}`);
    
    // Debug info - list all sections
    const allSections = document.querySelectorAll('.content-section');
    console.log(`Found ${allSections.length} total sections:`);
    allSections.forEach(section => {
        console.log(`- Section: ${section.id}, visible: ${!section.classList.contains('hidden')}, active: ${section.classList.contains('active')}`);
    });
    
    // Hide all sections
    allSections.forEach(function(section) {
        console.log(`Removing 'active' class from section: ${section.id}`);
        section.classList.remove('active');
    });
    
    // Show selected section
    const targetSection = document.getElementById(`section-${sectionId}`);
    if (targetSection) {
        console.log(`Target section found: ${targetSection.id}, adding 'active' class`);
        targetSection.classList.add('active');
        
        // Make sure it's not hidden
        targetSection.classList.remove('hidden');
    } else {
        console.error(`Target section not found: section-${sectionId}`);
        // Fallback to the build section if the target section doesn't exist
        const buildSection = document.getElementById('section-build');
        if (buildSection) {
            console.log('Falling back to build section');
            buildSection.classList.add('active');
            buildSection.classList.remove('hidden');
            sectionId = 'build';
        }
    }
    
    // Activate nav button
    document.querySelectorAll('.nav-button').forEach(function(btn) {
        console.log(`Processing nav button: ${btn.id}, current active: ${btn.classList.contains('active')}`);
        btn.classList.remove('active');
    });
    
    const targetBtn = document.getElementById(`nav-${sectionId}`);
    if (targetBtn) {
        console.log(`Target nav button found: ${targetBtn.id}, setting to active`);
        targetBtn.classList.add('active');
    } else {
        console.error(`Target nav button not found: nav-${sectionId}`);
    }
    
    // Special handling for sections needing dynamic content
    if (sectionId === 'flash') {
        // Update flash info when tab is shown
        updateFlashTabInfo();
        // Ensure flash progress is hidden initially when switching tabs
        hideFlashProgress(); 
    } else if (sectionId === 'donation') {
        renderDonationPage(); // Original donation page QR rendering
    } else if (sectionId === 'about') {
        // Generate LNURL QR code specifically for the About tab
        const lnurlAddressElement = document.getElementById('lnurl-about-address');
        if (lnurlAddressElement) {
            const lnurlAddress = lnurlAddressElement.textContent.trim();
            if (lnurlAddress) {
                generateQRCode('lnurl-about-qr', lnurlAddress, 'lightning');
            }
        } else {
            console.error('LNURL address element not found on About tab.');
        }
    }
}

// Build functions
function showTagSelection() {
    console.log('Showing tag selection');
    const tagSelection = document.getElementById('tag-selection');
    if (tagSelection) {
        tagSelection.classList.remove('hidden');
        fetchTags();
    }
}

function showBuildOptions() {
    console.log('Showing build options');
    // Hide tag selection if it's visible
    hideTagSelection();
    
    // Show build options
    const buildOptions = document.getElementById('build-options');
    if (buildOptions) {
        buildOptions.classList.remove('hidden');
    } else {
        console.error('Build options element not found');
    }
    
    // Update build button text AND ensure it's enabled
    const startBuildBtn = document.getElementById('start-build');
    if (startBuildBtn) {
        if (selectedTag === "latest" || !selectedTag) {
            startBuildBtn.textContent = 'Build Latest Stable Firmware';
        } else {
            startBuildBtn.textContent = `Build Firmware (${selectedTag})`;
        }
        startBuildBtn.disabled = false; // Ensure button is enabled
    }
}

function hideTagSelection() {
    console.log('Hiding tag selection');
    const tagSelection = document.getElementById('tag-selection');
    if (tagSelection) {
        tagSelection.classList.add('hidden');
    }
}

function fetchTags() {
    console.log('Fetching tags');
    if (isConnected) {
        socket.emit('get_tags');
    } else {
        console.error('Socket not connected, cannot fetch tags');
    }
}

function renderTagList(tags) {
    console.log('Rendering tag list');
    const tagList = document.getElementById('tag-list');
    if (!tagList) return;
    
    tagList.innerHTML = '';
    
    if (!tags || tags.length === 0) {
        tagList.innerHTML = '<p>No tags available.</p>';
        return;
    }
    
    tags.forEach(function(tag) {
        const tagItem = document.createElement('div');
        tagItem.classList.add('tag-item');
        tagItem.setAttribute('data-tag', tag);
        
        // Determine if it's a stable or dev tag
        if (tag.includes('stable') || tag.includes('release')) {
            tagItem.classList.add('stable');
        } else if (tag.includes('dev') || tag.includes('beta') || tag.includes('rc')) {
            tagItem.classList.add('dev');
        }
        
        tagItem.textContent = tag;
        tagItem.addEventListener('click', function() {
            selectTag(tag);
        });
        
        tagList.appendChild(tagItem);
    });
}

function selectTag(tag) {
    console.log(`Selecting tag: %c${tag}`, 'color: #f82b60; font-weight: bold');
    selectedTag = tag;
    
    // Update selected state in UI
    const tagItems = document.querySelectorAll('.tag-item');
    const tagSelectionInfo = document.getElementById('tag-selection-info');
    
    console.log(`Found ${tagItems.length} tag items`);
    
    tagItems.forEach(function(item) {
        const itemTag = item.getAttribute('data-tag');
        console.log(`Comparing tag: ${itemTag} with selected: ${tag}`);
        
        if (itemTag === tag) {
            console.log(`%cMatch found: ${itemTag}`, 'color: #34c759');
            item.classList.add('selected');
        } else {
            console.log(`%cNo match: ${itemTag}`, 'color: #aaaaaa');
            item.classList.remove('selected');
        }
    });
    
    // Update the info text
    if (tagSelectionInfo) {
        tagSelectionInfo.textContent = `Selected Tag: ${tag}`;
        tagSelectionInfo.style.color = 'var(--color-primary)';
    }
    
    // Update build button text
    const startBuildBtn = document.getElementById('start-build');
    if (startBuildBtn) {
        startBuildBtn.textContent = `Build Firmware (${tag})`;
    }

    // Immediately show build options after selecting a tag
    showBuildOptions();
}

function startBuild() {
    console.log(`Starting build with tag: ${selectedTag}`);

    if (!selectedTag) {
        console.error('No tag selected');
        showToast('Please select a tag or choose "Latest Stable" first.', 'error');
        return;
    }
    
    // Ensure the success message from previous build is hidden
    document.getElementById('build-complete')?.classList.add('hidden');

    buildInProgress = true;
    buildStartTime = Date.now();
    buildProgress = 0;
    updateBuildProgress(0, 'Preparing build...');
    clearBuildOutput();
    showBuildOutput();
    
    // Update the Clear Log button to show "Cancel"
    updateClearButtonText();
    
    // Disable build buttons
    const startBuildBtn = document.getElementById('start-build');
    if (startBuildBtn) startBuildBtn.disabled = true;
    document.getElementById('build-options').classList.add('hidden');
    document.getElementById('build-progress').classList.remove('hidden');
    
    let buildData = {};
    // Use the selected tag unless it's the special "latest" indicator
    if (selectedTag !== "latest") {
        buildData.tag = selectedTag;
    } // If it is "latest", send no tag (backend handles finding latest stable)

    // Send build request to backend
    fetch('/api/build', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(buildData),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Build initiated successfully');
            appendToBuildOutput('Build request sent to server...');
        } else {
            console.error('Error initiating build:', data.error);
            appendToBuildOutput(`Error initiating build: ${data.error}`);
            buildInProgress = false;
            updateBuildProgress(0, 'Build initiation failed');
             // Re-enable build button on initiation failure
            if (startBuildBtn) startBuildBtn.disabled = false;
        }
    })
    .catch((error) => {
        console.error('Error sending build request:', error);
        appendToBuildOutput(`Network error sending build request: ${error}`);
        buildInProgress = false;
        updateBuildProgress(0, 'Build request network error');
         // Re-enable build button on network failure
        if (startBuildBtn) startBuildBtn.disabled = false;
    });
}

function cancelBuild() {
    console.log('Cancel button clicked. Resetting UI to initial state.');
    
    // If a build is actually in progress, try to cancel it on the backend
    if (buildInProgress && isConnected) {
        console.log('Sending cancel_build event to server.');
        socket.emit('cancel_build'); // Assuming backend handles this
    }
    
    // Reset build state variables
    buildInProgress = false;
    selectedTag = null;
    buildProgress = 0;
    buildStartTime = null;

    // Reset UI elements to initial view
    document.getElementById('tag-selection')?.classList.add('hidden');
    document.getElementById('build-options')?.classList.add('hidden');
    document.getElementById('build-progress')?.classList.add('hidden');
    document.getElementById('build-complete')?.classList.add('hidden');
    
    // Ensure initial cards are visible (might not be strictly needed but good practice)
    document.querySelector('.card-container')?.classList.remove('hidden'); 

    // Reset build button state
    const startBuildBtn = document.getElementById('start-build');
    if (startBuildBtn) {
        startBuildBtn.disabled = false;
        startBuildBtn.textContent = 'Build Latest Stable Firmware'; // Reset to default
    }
    
    // Reset confirm tag button state (if it exists)
    const confirmTagBtn = document.getElementById('confirm-tag'); 
    if (confirmTagBtn) {
        confirmTagBtn.disabled = true;
    }

    // Clear build output area
    clearBuildOutput();
    updateBuildProgress(0, 'Build canceled or selection reset.'); 

    // Reset the output header title
    resetOutputHeaderTitle();

    console.log('UI reset complete.');
}

function updateBuildProgress(progress, message) {
    const progressBar = document.getElementById('build-progress-bar');
    const progressText = document.getElementById('build-progress-text');
    
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }
    
    if (progressText) {
        if (message) {
            progressText.textContent = `${progress}% - ${message}`;
        } else {
            progressText.textContent = `${progress}%`;
        }
    }
}

function showBuildOutput() {
    const buildOutput = document.getElementById('build-output');
    if (buildOutput) {
        buildOutput.classList.remove('hidden');
    }
}

function hideBuildOutput() {
    const buildOutput = document.getElementById('build-output');
    if (buildOutput) {
        buildOutput.classList.add('hidden');
    }
}

function toggleMaximizeOutput() {
    console.log('Toggling build output maximization');
    const outputContainer = document.querySelector('.output-container');
    const maximizeBtn = document.getElementById('maximize-output');

    if (!outputContainer || !maximizeBtn) {
        console.error('Cannot toggle maximize: container or button not found.');
        return;
    }

    const isMaximized = outputContainer.classList.contains('maximized');

    if (isMaximized) {
        // Minimize
        outputContainer.classList.remove('maximized');
        maximizeBtn.textContent = 'Maximize';
        maximizeBtn.title = 'Maximize Output';
        console.log('Build output minimized');
    } else {
        // Maximize
        outputContainer.classList.add('maximized');
        maximizeBtn.textContent = 'Minimize';
        maximizeBtn.title = 'Minimize Output';
        // Scroll to latest output when maximizing
        const buildOutput = document.getElementById('build-output');
        if(buildOutput) {
             buildOutput.scrollTop = buildOutput.scrollHeight;
        }
        console.log('Build output maximized');
    }
}

function copyBuildOutput() {
    const copyButton = document.getElementById('copy-output');
    const originalButtonText = copyButton.textContent;
    copyButton.textContent = 'Copying...';
    copyButton.disabled = true;

    fetch('/api/build_log')
        .then(response => {
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Build log not found. Run a build first.');
                }
                throw new Error(`Failed to fetch build log: ${response.statusText}`);
            }
            return response.text(); // Get the log content as plain text
        })
        .then(logContent => {
            navigator.clipboard.writeText(logContent)
                .then(() => {
                    copyButton.textContent = 'Copied!';
                    showToast('Full build log copied to clipboard', 'success');
                    // Optionally reset button text after a delay
                    setTimeout(() => {
                        copyButton.textContent = originalButtonText;
                        copyButton.disabled = false;
                    }, 2000); 
                })
                .catch(err => {
                    console.error('Failed to copy full log: ', err);
                    showToast('Failed to copy log to clipboard', 'error');
                    copyButton.textContent = 'Error';
                    // Reset button text after error
                    setTimeout(() => {
                        copyButton.textContent = originalButtonText;
                        copyButton.disabled = false;
                    }, 3000);
                });
        })
        .catch(err => {
            console.error('Error fetching build log:', err);
            showToast(err.message || 'Error fetching build log', 'error');
            copyButton.textContent = 'Error';
            // Reset button text after error
            setTimeout(() => {
                copyButton.textContent = originalButtonText;
                copyButton.disabled = false;
            }, 3000);
        });
}

function clearBuildOutput() {
    const buildOutput = document.getElementById('build-output');
    if (buildOutput) {
        buildOutput.textContent = '';
    }
}

function appendToBuildOutput(message) {
    const buildOutput = document.getElementById('build-output');
    if (buildOutput) {
        const line = document.createElement('div');
        line.textContent = message;
        
        // Apply styling based on message content
        if (message.toLowerCase().includes('error')) {
            line.classList.add('log-error');
        } else if (message.toLowerCase().includes('warning')) {
            line.classList.add('log-warning');
        } else if (message.toLowerCase().includes('success') || message.toLowerCase().includes('completed')) {
            line.classList.add('log-success');
        } else if (message.toLowerCase().includes('progress') || message.toLowerCase().includes('%')) {
            line.classList.add('log-progress');
        } else if (message.toLowerCase().includes('info')) {
            line.classList.add('log-info');
        }
        
        buildOutput.appendChild(line);
        buildOutput.scrollTop = buildOutput.scrollHeight;
    }
}

function getBuildOutputText() {
    const buildOutput = document.getElementById('build-output');
    if (buildOutput) {
        return buildOutput.textContent;
    }
    return '';
}

// Flash functions
function refreshDevices() {
    console.log('Refreshing devices');
    
    if (!isConnected) {
        console.error('Socket not connected, cannot refresh devices');
        return;
    }
    
    socket.emit('get_devices');
}

function renderDevices(devices) {
    console.log('Rendering devices');
    const devicesContainer = document.getElementById('devices-container');
    if (!devicesContainer) return;
    
    devicesContainer.innerHTML = '';
    
    if (!devices || devices.length === 0) {
        devicesContainer.innerHTML = '<p>No devices found. Connect a device and refresh.</p>';
        
        // Disable flash button
        const flashDeviceBtn = document.getElementById('flash-device');
        if (flashDeviceBtn) {
            flashDeviceBtn.disabled = true;
        }
        
        return;
    }
    
    devices.forEach(function(device) {
        const deviceItem = document.createElement('div');
        deviceItem.classList.add('device-item');
        deviceItem.setAttribute('data-device', device.port);
        
        deviceItem.innerHTML = `
            <div class="device-info">
                <div class="device-name">${device.port}</div>
                <div class="device-type">${device.description || 'Unknown device'}</div>
            </div>
        `;
        
        deviceItem.addEventListener('click', function() {
            selectDevice(device.port);
        });
        
        devicesContainer.appendChild(deviceItem);
    });
    
    // Select first device by default
    if (devices.length > 0) {
        selectDevice(devices[0].port);
    }
}

function selectDevice(devicePort) {
    console.log(`Selecting device: ${devicePort}`);
    selectedDeviceIP = devicePort;
    
    // Update selected state in UI
    const deviceItems = document.querySelectorAll('.device-item');
    
    deviceItems.forEach(function(item) {
        if (item.getAttribute('data-device') === devicePort) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
    
    // Enable flash button
    const flashDeviceBtn = document.getElementById('flash-device');
    if (flashDeviceBtn) {
        flashDeviceBtn.disabled = false;
        
        // Update button text to include firmware version if we have a stored build selected
        const selectedBuild = getSelectedStoredBuild();
        if (selectedBuild) {
            flashDeviceBtn.textContent = `Flash ${selectedBuild.firmware_version || selectedBuild.tag}`;
        } else {
            flashDeviceBtn.textContent = 'Flash Device';
        }
    }
}

function flashDevice() {
    selectedDeviceIP = document.getElementById('flash-ip').value.trim(); // Get current IP
    
    if (!selectedDeviceIP) {
        showToast('Please enter the device IP address.', 'error');
        return;
    }
    
    if (!lastSuccessfulBuild || !lastSuccessfulBuild.firmware_version) {
         showToast('No firmware build available to flash.', 'error');
         return;
    }

    const firmwareVersion = lastSuccessfulBuild.firmware_version;

    // --- Confirmation Dialog ---
    const confirmationMessage = `You are about to flash Version ${firmwareVersion} to device at IP ${selectedDeviceIP}.\n\nThis will update both the core firmware and the web interface.\n\nProceed?`;
    
    if (confirm(confirmationMessage)) {
        console.log(`Starting flash for ${selectedDeviceIP} with version ${firmwareVersion}`);
        
        // Show progress indicator
        showFlashProgress();
        clearFlashOutput(); // Clear previous logs
        
        // Disable button during flash
        const flashButton = document.getElementById('start-flash');
        if (flashButton) flashButton.disabled = true;

        // Send command to backend
        socket.emit('flash_device', { 
            ip_address: selectedDeviceIP,
            // No options needed, backend uses last successful build implicitly
        });
    } else {
        console.log('Flash cancelled by user.');
    }
}

function showFlashProgress() {
    const progressSection = document.getElementById('flash-progress');
    if (progressSection) {
        progressSection.classList.remove('hidden');
    }
    // Reset elements
    const statusElem = document.getElementById('flash-status');
    const messageElem = document.getElementById('flash-message');
    const spinnerElem = document.getElementById('flash-spinner');
    const progressBarContainer = document.getElementById('flash-progress-bar-container');
    const progressBar = document.getElementById('flash-progress-bar');
    const outputContainer = document.getElementById('flash-output-container');

    if (statusElem) statusElem.textContent = 'Flashing...';
    if (messageElem) messageElem.textContent = 'Initiating flash process...';
    if (spinnerElem) {
         spinnerElem.style.display = 'block'; // Show spinner
         spinnerElem.innerHTML = ''; // Clear any checkmark/error icons
         spinnerElem.className = 'progress-spinner'; // Reset class
    }
    if (progressBarContainer) progressBarContainer.style.display = 'none'; // Hide progress bar initially
    if (progressBar) {
        // Smooth transition for progress bar
        progressBar.style.transition = 'width 0.3s ease-in-out';
        progressBar.style.width = '0%';
    }
    if (outputContainer) outputContainer.style.display = 'none'; // Hide output log initially
    clearFlashOutput(); // Clear log content
}

function hideFlashProgress() {
     const progressSection = document.getElementById('flash-progress');
    if (progressSection) {
        progressSection.classList.add('hidden');
    }
}

function updateFlashProgress(data) {
    const statusElem = document.getElementById('flash-status');
    const messageElem = document.getElementById('flash-message');
    const spinnerElem = document.getElementById('flash-spinner');
    const progressBarContainer = document.getElementById('flash-progress-bar-container');
    const progressBar = document.getElementById('flash-progress-bar');
    const outputContainer = document.getElementById('flash-output-container');
    const flashButton = document.getElementById('start-flash');

    if (!statusElem || !messageElem || !spinnerElem) {
        console.error('Flash progress elements not found!');
        return;
    }

    // Append message to log regardless of status
    if (data.message) {
        appendToFlashOutput(data.message);
        // Optionally show the log container as soon as there's output
        if (outputContainer) outputContainer.style.display = 'block'; 
    }

    // Update main status message
    if (data.message) { // Use message for the short status too
        messageElem.textContent = data.message;
    }

    // Handle different statuses
    if (data.status === 'started' || data.status === 'progress') {
        statusElem.textContent = 'Flashing in Progress...';
        spinnerElem.style.display = 'block'; // Ensure spinner is visible
        
        // Update progress bar if percentage is provided
        if (typeof data.progress === 'number' && progressBarContainer && progressBar) {
            progressBarContainer.style.display = 'block';
            progressBar.style.width = `${data.progress}%`;
            messageElem.textContent = `${data.message || 'Progress'} (${data.progress}%)`; // Append percentage
        } else if (progressBarContainer) {
            // Maybe hide bar if no percentage, or show indeterminate
            // progressBarContainer.style.display = 'none'; 
        }

    } else if (data.status === 'completed') {
        statusElem.textContent = 'Flash Complete';
        messageElem.textContent = data.message || 'Firmware flashed successfully!';
        spinnerElem.style.display = 'none'; // Hide spinner
        // Optionally show a success icon
        // spinnerElem.innerHTML = '<svg>...</svg>'; 
        showToast('Flash completed successfully!', 'success');
        if (flashButton) flashButton.disabled = false; // Re-enable button

    } else if (data.status === 'error') {
        statusElem.textContent = 'Flash Failed';
        statusElem.style.color = 'var(--color-error)';
        messageElem.textContent = `Error: ${data.message || 'An unknown error occurred.'}`;
        spinnerElem.style.display = 'none'; // Hide spinner
         // Optionally show an error icon
         // spinnerElem.innerHTML = '<svg>...</svg>'; 
        showToast(`Flash failed: ${data.message || 'Unknown error'}`, 'error');
        if (flashButton) flashButton.disabled = false; // Re-enable button on error too

    } else {
         // Default/unknown status
         messageElem.textContent = data.message || 'Updating status...';
    }
}

function clearFlashOutput() {
    const outputElem = document.getElementById('flash-output');
    if (outputElem) {
        outputElem.textContent = '';
    }
    // Optionally hide the container again
    // const outputContainer = document.getElementById('flash-output-container');
    // if (outputContainer) outputContainer.style.display = 'none';
}

function appendToFlashOutput(message) {
    const outputElem = document.getElementById('flash-output');
    if (outputElem) {
        outputElem.textContent += message + '\n';
        // Auto-scroll to bottom
        outputElem.scrollTop = outputElem.scrollHeight; 
    }
}

function copyFlashOutput() {
    const outputElem = document.getElementById('flash-output');
    if (outputElem && navigator.clipboard) {
        navigator.clipboard.writeText(outputElem.textContent)
            .then(() => showToast('Flash log copied to clipboard!', 'success'))
            .catch(err => {
                console.error('Failed to copy flash log:', err);
                showToast('Failed to copy flash log.', 'error');
            });
    } else {
        showToast('Clipboard API not available.', 'error');
    }
}

// Stored builds functions
function storeBuild(buildData) {
    console.log('Storing build:', buildData);
    
    // Add to stored builds array
    storedBuilds.push(buildData);
    
    // Save to localStorage
    saveStoredBuilds();
    
    // Render stored builds if we're on that section
    const storedSection = document.getElementById('section-stored');
    if (storedSection && storedSection.classList.contains('active')) {
        renderStoredBuilds();
    }
}

function loadStoredBuilds() {
    console.log('Loading stored builds');
    
    try {
        const storedData = localStorage.getItem('storedBuilds');
        if (storedData) {
            storedBuilds = JSON.parse(storedData);
            console.log(`Loaded ${storedBuilds.length} stored builds`);
        }
    } catch (error) {
        console.error('Error loading stored builds:', error);
        storedBuilds = [];
    }
}

function saveStoredBuilds() {
    console.log(`Saving ${storedBuilds.length} builds`);
    
    try {
        localStorage.setItem('storedBuilds', JSON.stringify(storedBuilds));
    } catch (error) {
        console.error('Error saving stored builds:', error);
    }
}

function renderStoredBuilds() {
    console.log('Rendering stored builds');
    const buildsContainer = document.getElementById('stored-builds-container');
    if (!buildsContainer) return;
    
    buildsContainer.innerHTML = '';
    
    if (storedBuilds.length === 0) {
        buildsContainer.innerHTML = '<p>No stored builds. Build some firmware first.</p>';
        return;
    }
    
    // Sort by timestamp (newest first)
    storedBuilds.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    storedBuilds.forEach(function(build, index) {
        const buildDate = new Date(build.timestamp).toLocaleString();
        const buildItem = document.createElement('div');
        buildItem.classList.add('build-item');
        buildItem.setAttribute('data-index', index);
        
        buildItem.innerHTML = `
            <div class="build-info">
                <div class="build-tag">${build.firmware_version || build.tag}</div>
                <div class="build-date">${buildDate}</div>
                <div class="build-duration">Build time: ${build.duration}s</div>
            </div>
            <div class="build-actions">
                <button class="btn btn-sm flash-build">Flash</button>
                <button class="btn btn-sm download-build">Download</button>
                <button class="btn btn-sm delete-build">Delete</button>
            </div>
        `;
        
        // Add click event for selecting the build
        buildItem.addEventListener('click', function(e) {
            if (!e.target.classList.contains('btn')) {
                selectStoredBuild(index);
            }
        });
        
        // Add button events
        const flashBtn = buildItem.querySelector('.flash-build');
        if (flashBtn) {
            flashBtn.addEventListener('click', function() {
                selectStoredBuild(index);
                showSection('flash');
            });
        }
        
        const downloadBtn = buildItem.querySelector('.download-build');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', function() {
                downloadBuildByIndex(index);
            });
        }
        
        const deleteBtn = buildItem.querySelector('.delete-build');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', function() {
                deleteStoredBuild(index);
            });
        }
        
        buildsContainer.appendChild(buildItem);
    });
}

function selectStoredBuild(index) {
    console.log(`Selecting stored build at index ${index}`);
    
    // Update selected state in UI
    const buildItems = document.querySelectorAll('.build-item');
    
    buildItems.forEach(function(item) {
        if (parseInt(item.getAttribute('data-index')) === index) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
    
    // Update flash button text if we're on the flash section
    const flashDeviceBtn = document.getElementById('flash-device');
    if (flashDeviceBtn && selectedDeviceIP) {
        const build = storedBuilds[index];
        if (build) {
            flashDeviceBtn.textContent = `Flash ${build.firmware_version || build.tag}`;
        }
    }
}

function getSelectedStoredBuild() {
    const selectedBuildItem = document.querySelector('.build-item.selected');
    if (selectedBuildItem) {
        const index = parseInt(selectedBuildItem.getAttribute('data-index'));
        return storedBuilds[index];
    }
    return null;
}

function downloadBuild() {
    const selectedBuild = getSelectedStoredBuild();
    if (selectedBuild) {
        downloadBuildByIndex(storedBuilds.indexOf(selectedBuild));
    } else {
        console.error('No build selected for download');
    }
}

function downloadBuildByIndex(index) {
    console.log(`Downloading build at index ${index}`);
    
    const build = storedBuilds[index];
    if (!build || !build.path) {
        console.error('Build not found or no path available');
        return;
    }
    
    // Request download from server
    if (isConnected) {
        socket.emit('download_build', { path: build.path });
    } else {
        console.error('Socket not connected, cannot download build');
    }
}

function deleteSelectedBuild() {
    const selectedBuildItem = document.querySelector('.build-item.selected');
    if (selectedBuildItem) {
        const index = parseInt(selectedBuildItem.getAttribute('data-index'));
        deleteStoredBuild(index);
    } else {
        console.error('No build selected for deletion');
    }
}

function deleteStoredBuild(index) {
    console.log(`Deleting build at index ${index}`);
    
    if (index >= 0 && index < storedBuilds.length) {
        const deleted = storedBuilds.splice(index, 1)[0];
        console.log('Deleted build:', deleted);
        
        // Update localStorage
        saveStoredBuilds();
        
        // Re-render the list
        renderStoredBuilds();
    }
}

// Donation functions
function renderDonationPage() {
    console.log('Rendering donation page with QR codes');
    
    // Get the donation-qr elements from the index.html
    const btcQR = document.querySelector('#section-donation .donation-option:nth-of-type(1) .donation-qr');
    const lightningQR = document.querySelector('#section-donation .donation-option:nth-of-type(2) .donation-qr');
    
    // Get the donation addresses
    const btcAddress = document.querySelector('#section-donation .donation-option:nth-of-type(1) .donation-address').textContent.trim();
    const lightningAddress = document.querySelector('#section-donation .donation-option:nth-of-type(2) .donation-address').textContent.trim();
    
    console.log(`Found donation addresses: BTC=${btcAddress}, Lightning=${lightningAddress}`);
    
    // Generate QR codes
    if (btcQR) {
        // Clear any existing content
        btcQR.innerHTML = '';
        console.log('Generating BTC QR code');
        generateQRCode(btcQR, btcAddress, 'bitcoin');
    } else {
        console.error('BTC QR element not found');
    }
    
    if (lightningQR) {
        // Clear any existing content
        lightningQR.innerHTML = '';
        console.log('Generating Lightning QR code');
        generateQRCode(lightningQR, lightningAddress, 'lightning');
    } else {
        console.error('Lightning QR element not found');
    }
    
    // Add copy button functionality
    document.querySelectorAll('.copy-address-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const address = this.getAttribute('data-address');
            navigator.clipboard.writeText(address).then(
                function() {
                    // Success
                    console.log('Address copied:', address);
                    showToast('Address copied to clipboard!', 'success');
                },
                function(err) {
                    // Error
                    console.error('Failed to copy address:', err);
                    showToast('Failed to copy address', 'error');
                }
            );
        });
    });
}

function generateQRCode(element, data, type = 'text') {
    if (!element) {
        console.error(`Element not found for QR code generation`);
        return;
    }
    
    // If element is a string (ID), get the actual element
    if (typeof element === 'string') {
        const el = document.getElementById(element);
        if (!el) {
            console.error(`Element with ID ${element} not found for QR code generation`);
            return;
        }
        element = el;
    }
    
    // Clear any existing content
    element.innerHTML = '';
    
    let qrText = data;
    
    // Format based on type
    if (type === 'bitcoin') {
        qrText = `bitcoin:${data}`;
    } else if (type === 'ethereum') {
        qrText = `ethereum:${data}`;
    } else if (type === 'lightning') {
        qrText = `lightning:${data}`;
    }
    
    console.log(`Generating QR code with data: ${qrText}`);
    
    try {
        // Create QR code
        new QRCode(element, {
            text: qrText,
            width: 180,
            height: 180,
            colorDark: '#000000',
            colorLight: '#ffffff',
            correctLevel: QRCode.CorrectLevel.H
        });
        console.log('QR code generated successfully');
    } catch (err) {
        console.error('Error generating QR code:', err);
        
        // Fallback method - try again after a delay
        setTimeout(() => {
            try {
                console.log('Trying QR code generation again...');
                element.innerHTML = ''; // Clear again to be safe
                new QRCode(element, {
                    text: qrText,
                    width: 180,
                    height: 180,
                    colorDark: '#000000',
                    colorLight: '#ffffff',
                    correctLevel: QRCode.CorrectLevel.H
                });
                console.log('QR code generated successfully on second attempt');
            } catch (retryErr) {
                console.error('Failed to generate QR code on retry:', retryErr);
                element.innerHTML = '<div class="qr-error">QR Generation Failed</div>';
            }
        }, 1000);
    }
}

// Utility functions
function updateConnectionStatus(connected) {
    const statusIndicator = document.getElementById('connection-status');
    if (statusIndicator) {
        if (connected) {
            statusIndicator.textContent = 'Connected';
            statusIndicator.classList.add('connected');
            statusIndicator.classList.remove('disconnected');
        } else {
            statusIndicator.textContent = 'Disconnected';
            statusIndicator.classList.add('disconnected');
            statusIndicator.classList.remove('connected');
        }
    }
}

function checkServerStatus() {
    console.log('Checking server status...');
    
    // Simple HEAD request to check if server is up
    fetch('/api/status', { method: 'GET' })
        .then(response => {
            if (response.ok) {
                console.log('Server is up');
                updateConnectionStatus(true);
            } else {
                console.log('Server returned error status');
                updateConnectionStatus(false);
            }
        })
        .catch(error => {
            console.error('Error checking server status:', error);
            updateConnectionStatus(false);
        });
}

function showBuildNotification(title, message) {
    // Check if browser supports notifications
    if ('Notification' in window) {
        // Check if permission is already granted
        if (Notification.permission === 'granted') {
            createNotification(title, message);
        } 
        // Otherwise, request permission
        else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(function(permission) {
                if (permission === 'granted') {
                    createNotification(title, message);
                }
            });
        }
    }
    
    // Also show a toast notification in the app
    showToast(message, title.toLowerCase().includes('fail') ? 'error' : 'success');
}

function createNotification(title, message) {
    const notification = new Notification(title, {
        body: message,
        icon: '/static/img/logo.png'
    });
    
    notification.onclick = function() {
        window.focus();
        this.close();
    };
    
    // Auto close after 5 seconds
    setTimeout(notification.close.bind(notification), 5000);
}

function showToast(message, type = 'info') {
    // Create toast element if it doesn't exist
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.classList.add('toast');
        document.body.appendChild(toast);
    }
    
    // Set type and message
    toast.className = 'toast';
    toast.classList.add(type);
    toast.textContent = message;
    
    // Show the toast
    toast.classList.add('show');
    
    // Hide after 3 seconds
    setTimeout(function() {
        toast.classList.remove('show');
    }, 3000);
}

function applyDarkTheme() {
    document.body.classList.remove('light-theme');
    document.body.classList.add('dark-theme');
}

function logSectionsAndButtons() {
    // Debug: Log sections
    console.log("--- Debug: Sections ---");
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => {
        console.log(`Section: ${section.id}, Active: ${section.classList.contains('active')}`);
    });

    // Debug: Log nav buttons and attach listener if missing
    console.log("--- Debug: Navigation Buttons ---");
    const navButtons = document.querySelectorAll('.app-nav .nav-button');
    navButtons.forEach(button => {
        const sectionId = button.id.replace('nav-', '');
        const hasListener = button.dataset.listenerAttached === 'true'; // Check custom attribute
        console.log(`Button: ${button.id}, Class list: ${button.className}, Event listeners attached: ${hasListener}`);
        // REMOVED redundant listener attachment
        // if (!hasListener) {
        //     console.warn(`Manually adding click event to ${button.id}`);
        //     button.addEventListener('click', () => showSection(sectionId));
        //     button.dataset.listenerAttached = 'true'; // Mark as attached
        // }
    });

    // Debug: Log option cards and attach listener if missing
    console.log("--- Debug: Option Cards ---");
    const buildLatestCard = document.getElementById('build-latest');
    if (buildLatestCard) {
        const hasListener = buildLatestCard.dataset.listenerAttached === 'true';
        console.log(`Card: build-latest, Click handler attached: ${hasListener}`);
        // REMOVED redundant listener attachment
        // if (!hasListener) {
        //     console.warn('Manually adding click event to build-latest card');
        //     buildLatestCard.addEventListener('click', function() {
        //         console.log('Build latest card clicked (from manual handler)');
        //         selectedTag = "latest"; // Set indicator
        //         showBuildOptions();
        //     });
        //     buildLatestCard.dataset.listenerAttached = 'true';
        // }
    }
    const buildTagCard = document.getElementById('build-tag');
    if (buildTagCard) {
        const hasListener = buildTagCard.dataset.listenerAttached === 'true';
        console.log(`Card: build-tag, Click handler attached: ${hasListener}`);
        // REMOVED redundant listener attachment
        // if (!hasListener) {
        //     console.warn('Manually adding click event to build-tag card');
        //     buildTagCard.addEventListener('click', function() {
        //         console.log('Build tag card clicked (from manual handler)');
        //         showTagSelection();
        //     });
        //     buildTagCard.dataset.listenerAttached = 'true';
        // }
    }
}

function createBuildInfoQRCode(buildInfo) {
    // Check if an element for the QR code exists, if not create one
    let qrElement = document.getElementById('build-info-qr');
    if (!qrElement) {
        // Create container
        const container = document.createElement('div');
        container.classList.add('build-info-qr-container');
        
        // Add title
        const title = document.createElement('h3');
        title.textContent = 'Scan to Share Build Info';
        
        // Create QR element
        qrElement = document.createElement('div');
        qrElement.id = 'build-info-qr';
        qrElement.classList.add('build-qr');
        
        // Add to container
        container.appendChild(title);
        container.appendChild(qrElement);
        
        // Find the build complete section and append the container
        const buildCompleteSection = document.getElementById('build-complete');
        if (buildCompleteSection) {
            // Insert before the button group
            const buttonGroup = buildCompleteSection.querySelector('.button-group');
            if (buttonGroup) {
                buildCompleteSection.insertBefore(container, buttonGroup);
            } else {
                buildCompleteSection.appendChild(container);
            }
            
            console.log('Added QR code container to build complete section');
        } else {
            console.error('Could not find build complete section');
            return;
        }
    }
    
    // Create data for QR code - simple JSON with build info
    const qrData = JSON.stringify({
        version: buildInfo.version || 'unknown',
        buildTime: buildInfo.buildTime || new Date().toISOString(),
        tag: buildInfo.tag || 'latest',
        url: window.location.href
    });
    
    // Generate QR code
    generateQRCode('build-info-qr', qrData);
    
    console.log('Generated build info QR code');
}

function createDeviceInfoQRCode(deviceInfo) {
    // Check if an element for the QR code exists, if not create one
    let qrElement = document.getElementById('device-info-qr');
    if (!qrElement) {
        // Create container
        const container = document.createElement('div');
        container.classList.add('device-info-qr-container');
        
        // Add title
        const title = document.createElement('h3');
        title.textContent = 'Scan to Connect to Device';
        
        // Create QR element
        qrElement = document.createElement('div');
        qrElement.id = 'device-info-qr';
        qrElement.classList.add('device-qr');
        
        // Add to container
        container.appendChild(title);
        container.appendChild(qrElement);
        
        // Find a good location to insert this QR code
        const flashForm = document.querySelector('.flash-form');
        if (flashForm) {
            // Insert after the form group
            flashForm.appendChild(container);
            console.log('Added QR code container to flash form');
        } else {
            console.error('Could not find flash form');
            return;
        }
    }
    
    // Create data for QR code - simple JSON with device info
    const qrData = JSON.stringify({
        ip: deviceInfo.ip || document.getElementById('flash-ip')?.value || '192.168.1.100',
        type: deviceInfo.type || 'bitaxe',
        name: deviceInfo.name || 'BitaxeDevice',
        timestamp: new Date().toISOString()
    });
    
    // Generate QR code
    generateQRCode('device-info-qr', qrData);
    console.log('Generated device info QR code');
}

// Modify updateFlashButtonText function to ensure it always includes version
function updateFlashButtonText(version) {
    console.log(`Updating Flash button text with version: ${version}`);
    const flashButton = document.getElementById('start-flash');
    const gotoFlashButton = document.getElementById('goto-flash');
    
    // Ensure version is treated as a string and check prefix
    const versionString = String(version);
    const buttonText = versionString.toLowerCase().startsWith('v') 
                       ? `Flash Device (${versionString})` 
                       : `Flash Device (v${versionString})`;

    if (flashButton) {
        flashButton.textContent = buttonText;
        flashButton.setAttribute('data-version', versionString);
    } else {
        console.warn('Flash button (#start-flash) not found, cannot update text');
    }
    
    // Also update the goto-flash button if it exists
    if (gotoFlashButton) {
        gotoFlashButton.textContent = buttonText;
    } else {
         console.warn('Goto Flash button (#goto-flash) not found, cannot update text');
    }
}

// Add function to handle copy address buttons
function setupCopyAddressButtons() {
    console.log('Setting up copy address buttons');
    document.querySelectorAll('.copy-address-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const address = this.getAttribute('data-address');
            if (!address) {
                console.error('No address found to copy');
                showToast('No address found to copy', 'error');
                return;
            }
            
            console.log('Copying address to clipboard:', address);
            navigator.clipboard.writeText(address).then(
                function() {
                    // Success
                    console.log('Address copied successfully');
                    showToast('Address copied to clipboard!', 'success');
                },
                function(err) {
                    // Error
                    console.error('Failed to copy address:', err);
                    showToast('Failed to copy address', 'error');
                }
            );
        });
    });
}

// Helper function to reset output header
function resetOutputHeaderTitle() {
    const outputHeaderTitle = document.querySelector('#build-progress .output-header h3');
    if (outputHeaderTitle) {
        outputHeaderTitle.textContent = 'Build Output';
    }
}

// Update the Clear Log button text based on build state
function updateClearButtonText() {
    const clearLogBtn = document.getElementById('clear-log-btn');
    if (clearLogBtn) {
        if (buildInProgress) {
            clearLogBtn.textContent = 'Cancel Build';
            clearLogBtn.title = 'Cancel the current build process';
            clearLogBtn.classList.add('cancel-button');
        } else {
            clearLogBtn.textContent = 'Clear Log';
            clearLogBtn.title = 'Clear build output log';
            clearLogBtn.classList.remove('cancel-button');
        }
    }
}

// --- NEW: Function to fetch last build info ---
function fetchLastBuildInfo() {
    if (isConnected) {
        console.log('Requesting last build info from server...');
        socket.emit('get_last_build');
    } else {
        console.log('Socket not connected, cannot fetch last build info.');
        // Optionally try to load from local storage as a fallback?
    }
}

// --- NEW: Function to update Flash tab based on last build info ---
function updateFlashTabInfo() {
    console.log('Updating Flash tab info. Last build:', lastSuccessfulBuild);
    const flashInfoVersionElem = document.querySelector('#flash-available-version .version-highlight');
    const flashButton = document.getElementById('start-flash');

    if (flashInfoVersionElem) {
        if (lastSuccessfulBuild && lastSuccessfulBuild.firmware_version) {
            flashInfoVersionElem.textContent = `${lastSuccessfulBuild.firmware_version}`;
            flashInfoVersionElem.closest('#flash-available-version').style.color = 'var(--color-text-secondary)'; // Reset color
        } else {
            flashInfoVersionElem.textContent = 'No build available';
            flashInfoVersionElem.closest('#flash-available-version').style.color = 'var(--color-warning)'; // Use warning color
        }
    } else {
        console.error('#flash-available-version .version-highlight element not found!');
    }
    
    updateFlashButtonState(); // Update button text and disabled state
}

// --- NEW: Function to update flash button state ---
function updateFlashButtonState() {
    const flashButton = document.getElementById('start-flash');
    if (!flashButton) return;

    selectedDeviceIP = document.getElementById('flash-ip').value.trim(); // Ensure IP is current

    // ---> More explicit check for lastSuccessfulBuild and its version <--- 
    if (lastSuccessfulBuild && typeof lastSuccessfulBuild === 'object' && lastSuccessfulBuild.firmware_version && selectedDeviceIP) {
        flashButton.textContent = `Flash Device (${lastSuccessfulBuild.firmware_version})`;
        flashButton.disabled = false;
    } else {
        flashButton.textContent = 'Flash Device'; // Default text
        flashButton.disabled = true; // Disable if no build or no IP
    }
     console.log(`Flash button updated. Text: "${flashButton.textContent}", Disabled: ${flashButton.disabled}`);
} 
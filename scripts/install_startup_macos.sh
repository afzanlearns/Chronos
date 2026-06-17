#!/bin/bash
PLIST_PATH="$HOME/Library/LaunchAgents/com.chronos.tracker.plist"

cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.chronos.tracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/chronos</string>
        <string>serve</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

launchctl load "$PLIST_PATH"
echo "Chronos added to macOS startup."

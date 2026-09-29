import QtQuick
import QtQuick.Controls
import "../components"

Item {
    id: root

    property int activeTab: 0
    property bool devMode: settingsController.get("developer_mode") === true
    property var engineStatus: null
    property var troubleshootStatus: null
    property string dllOutput: ""

    Connections {
        target: settingsController
        function onEngineStatusUpdated(status) {
            root.engineStatus = status
        }
        function onEngineUpdateProgress(msg) {
            appController.showToast(msg, "info")
        }
        function onEngineUpdateFinished(success, msg) {
            appController.showToast(msg, success ? "success" : "error")
        }
        function onTroubleshootStatusUpdated(status) {
            root.troubleshootStatus = status
        }
        function onLoadedDllsUpdated(output) {
            root.dllOutput = output
        }
    }

    Component.onCompleted: {
        settingsController.loadEngineVersionsAsync()
        if (root.devMode) {
            settingsController.runTroubleshoot()
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        // Page Header + Reset
        Row {
            width: parent.width

            Text {
                text: "Settings"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 24
                font.weight: Font.Bold
                color: appController.textPrimaryColor
                anchors.verticalCenter: parent.verticalCenter
            }

            Item { width: Math.max(0, parent.width - 280); height: 1 }

            ModernButton {
                text: "Reset to Defaults"
                variant: "danger"
                onClicked: {
                    settingsController.resetDefaults()
                    appController.setTheme("dark")
                    appController.setAccent("Rose")
                    appController.showToast("Settings reset to defaults", "info")
                }
            }
        }

        // Tabs Header Row
        Row {
            spacing: 8

            Repeater {
                model: {
                    var tabs = [
                        { idx: 0, label: "General", icon: "⚙" },
                        { idx: 1, label: "Appearance", icon: "🎨" },
                        { idx: 2, label: "Download", icon: "📥" },
                        { idx: 3, label: "Playlist & Queue", icon: "📋" },
                        { idx: 4, label: "Advanced", icon: "🔧" }
                    ]
                    if (root.devMode) {
                        tabs.push({ idx: 5, label: "Troubleshoot", icon: "🛠" })
                    }
                    return tabs
                }

                delegate: Rectangle {
                    height: 36
                    width: tabText.implicitWidth + 28
                    radius: 8
                    color: root.activeTab === modelData.idx ? appController.primaryColor : (tabMouse.containsMouse ? appController.surfaceVariantColor : appController.surfaceColor)
                    border.width: 1
                    border.color: root.activeTab === modelData.idx ? appController.primaryColor : appController.borderColor

                    Behavior on color { ColorAnimation { duration: 120 } }

                    Row {
                        id: tabText
                        anchors.centerIn: parent
                        spacing: 6

                        Text {
                            text: modelData.icon
                            font.pixelSize: 13
                            color: root.activeTab === modelData.idx ? "#ffffff" : appController.textSecondaryColor
                        }

                        Text {
                            text: modelData.label
                            font.family: "Segoe UI, Inter, sans-serif"
                            font.pixelSize: 12
                            font.weight: root.activeTab === modelData.idx ? Font.DemiBold : Font.Medium
                            color: root.activeTab === modelData.idx ? "#ffffff" : appController.textSecondaryColor
                        }
                    }

                    MouseArea {
                        id: tabMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.activeTab = modelData.idx
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: appController.borderColor
        }

        // Tab Content Area
        ScrollView {
            width: parent.width
            height: parent.height - 120
            clip: true

            Column {
                width: parent.width - 16
                spacing: 18

                // ════════════════ TAB 0: GENERAL ════════════════
                Column {
                    visible: root.activeTab === 0
                    width: parent.width
                    spacing: 16

                    Text { text: "General Behavior"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    ModernSwitch {
                        text: "Ask before closing"
                        subtitle: "Prompts to minimize to system tray or exit"
                        checked: settingsController.get("ask_on_close") !== false
                        onToggled: function(val) { settingsController.set("ask_on_close", val) }
                    }

                    Row {
                        spacing: 20
                        ModernTextField {
                            label: "Download Speed Limit (KB/s)"
                            placeholderText: "0 = Unlimited"
                            text: String(settingsController.get("speed_limit") || "0")
                            onTextEdited: settingsController.set("speed_limit", parseInt(text) || 0)
                        }

                        ModernDropdown {
                            label: "Auto Delete History"
                            currentValue: String(settingsController.get("auto_delete_history_days") || "0")
                            model: [
                                { text: "Never", value: "0" },
                                { text: "Older than 1 day", value: "1" },
                                { text: "Older than 3 days", value: "3" },
                                { text: "Older than 7 days", value: "7" },
                                { text: "Older than 30 days", value: "30" }
                            ]
                            onActivated: function(idx, val) { settingsController.set("auto_delete_history_days", parseInt(val)) }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                    Text { text: "Media & Processing"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    Flow {
                        width: parent.width
                        spacing: 20

                        ModernSwitch {
                            text: "Embed Thumbnail"
                            checked: settingsController.get("embed_thumbnail") !== false
                            onToggled: function(val) { settingsController.set("embed_thumbnail", val) }
                        }

                        ModernSwitch {
                            text: "Embed Metadata"
                            checked: settingsController.get("embed_metadata") !== false
                            onToggled: function(val) { settingsController.set("embed_metadata", val) }
                        }

                        ModernSwitch {
                            text: "Save with Chapters"
                            checked: settingsController.get("embed_chapters") !== false
                            onToggled: function(val) { settingsController.set("embed_chapters", val) }
                        }

                        ModernSwitch {
                            text: "Embed Subtitles"
                            checked: settingsController.get("embed_subtitles") === true
                            onToggled: function(val) { settingsController.set("embed_subtitles", val) }
                        }
                    }

                    ModernTextField {
                        width: 320
                        label: "Subtitle Language(s)"
                        placeholderText: "e.g. en, es, hi or all"
                        text: settingsController.get("auto_subtitle_lang") || "en"
                        onTextEdited: settingsController.set("auto_subtitle_lang", text)
                    }

                    Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                    Text { text: "SponsorBlock (YouTube)"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    ModernSwitch {
                        text: "Enable SponsorBlock"
                        subtitle: "Automatically cut or mark sponsor segments and intros"
                        checked: settingsController.get("enable_sponsorblock") === true
                        onToggled: function(val) { settingsController.set("enable_sponsorblock", val) }
                    }

                    ModernDropdown {
                        label: "SponsorBlock Action Mode"
                        currentValue: settingsController.get("sponsorblock_action") || "remove"
                        model: [
                            { text: "Cut Segments (Remove)", value: "remove" },
                            { text: "Mark with Chapters", value: "mark" },
                            { text: "Cut Sponsors & Mark Others", value: "remove_and_mark" }
                        ]
                        onActivated: function(idx, val) { settingsController.set("sponsorblock_action", val) }
                    }
                }

                // ════════════════ TAB 1: APPEARANCE ════════════════
                Column {
                    visible: root.activeTab === 1
                    width: parent.width
                    spacing: 16

                    Text { text: "Theme Mode"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    Row {
                        spacing: 12

                        ModernButton {
                            text: "Dark Mode"
                            variant: appController.themeMode === "dark" ? "primary" : "secondary"
                            onClicked: appController.setTheme("dark")
                        }

                        ModernButton {
                            text: "Light Mode"
                            variant: appController.themeMode === "light" ? "primary" : "secondary"
                            onClicked: appController.setTheme("light")
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                    Text { text: "Accent Color"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    Row {
                        spacing: 12

                        Repeater {
                            model: [
                                { name: "Rose", color: "#f43f5e" },
                                { name: "Indigo", color: "#6366f1" },
                                { name: "Emerald", color: "#10b981" },
                                { name: "Amber", color: "#f59e0b" },
                                { name: "Violet", color: "#8b5cf6" },
                                { name: "Sky", color: "#0ea5e9" }
                            ]

                            delegate: Rectangle {
                                width: 36
                                height: 36
                                radius: 18
                                color: modelData.color
                                border.width: appController.accentName === modelData.name ? 3 : 1
                                border.color: appController.accentName === modelData.name ? "#ffffff" : appController.borderColor

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: appController.setAccent(modelData.name)
                                }
                            }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                    Text { text: "Background Image Overlay"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    Row {
                        spacing: 12

                        Repeater {
                            model: [
                                { name: "Minimal", path: "/bg_4.png" },
                                { name: "Neon Grid", path: "/bg_1.png" },
                                { name: "Ethereal", path: "/bg_2.png" },
                                { name: "Circuit", path: "/bg_3.png" }
                            ]

                            delegate: Rectangle {
                                width: 120
                                height: 60
                                radius: 8
                                color: appController.surfaceVariantColor
                                border.width: appController.bgImagePath === modelData.path ? 2 : 1
                                border.color: appController.bgImagePath === modelData.path ? appController.primaryColor : appController.borderColor

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.name
                                    font.family: "Segoe UI, Inter, sans-serif"
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    color: appController.textPrimaryColor
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: appController.setBgImage(modelData.path)
                                }
                            }
                        }
                    }

                    Row {
                        spacing: 10

                        ModernButton {
                            text: "Browse Custom Image..."
                            variant: "secondary"
                            onClicked: {
                                var img = settingsController.browseBgImage()
                                if (img !== "") appController.setBgImage(img)
                            }
                        }

                        ModernButton {
                            text: "Clear Image"
                            variant: "ghost"
                            onClicked: appController.setBgImage("")
                        }
                    }

                    Column {
                        spacing: 6
                        Text { text: "Image Opacity: " + Math.round(appController.bgImageOpacity * 100) + "%"; font.pixelSize: 12; color: appController.textSecondaryColor }

                        Slider {
                            width: 300
                            from: 0.0
                            to: 0.5
                            stepSize: 0.02
                            value: appController.bgImageOpacity
                            onMoved: appController.setBgOpacity(value)
                        }
                    }
                }

                // ════════════════ TAB 2: DOWNLOAD ════════════════
                Column {
                    visible: root.activeTab === 2
                    width: parent.width
                    spacing: 16

                    Text { text: "Download Paths"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    Row {
                        width: parent.width
                        spacing: 10

                        ModernTextField {
                            id: defaultPathField
                            width: parent.width - 100
                            label: "Default Download Directory"
                            text: settingsController.get("default_download_path") || ""
                            readOnly: true
                        }

                        ModernButton {
                            text: "Browse"
                            variant: "secondary"
                            customHeight: 42
                            anchors.bottom: defaultPathField.bottom
                            onClicked: {
                                var res = settingsController.browseFolder(defaultPathField.text)
                                if (res !== "") {
                                    defaultPathField.text = res
                                    settingsController.set("default_download_path", res)
                                }
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        ModernTextField {
                            id: tempPathField
                            width: parent.width - 100
                            label: "Temporary Processing Directory"
                            text: settingsController.get("temp_download_path") || ""
                            readOnly: true
                        }

                        ModernButton {
                            text: "Browse"
                            variant: "secondary"
                            customHeight: 42
                            anchors.bottom: tempPathField.bottom
                            onClicked: {
                                var res = settingsController.browseFolder(tempPathField.text)
                                if (res !== "") {
                                    tempPathField.text = res
                                    settingsController.set("temp_download_path", res)
                                }
                            }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                    Text { text: "Default Formats & Quality"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    Row {
                        spacing: 20

                        ModernDropdown {
                            label: "Preferred Quality"
                            currentValue: settingsController.get("preferred_format") || "best"
                            model: [
                                { text: "Best Quality (Default)", value: "best" },
                                { text: "1080p (Full HD)", value: "bestvideo[height<=1080]+bestaudio/best" },
                                { text: "720p (HD)", value: "bestvideo[height<=720]+bestaudio/best" },
                                { text: "480p", value: "bestvideo[height<=480]+bestaudio/best" },
                                { text: "Audio Only", value: "bestaudio/best" }
                            ]
                            onActivated: function(idx, val) { settingsController.set("preferred_format", val) }
                        }

                        ModernDropdown {
                            label: "Audio Codec"
                            currentValue: settingsController.get("audio_codec") || "mp3"
                            model: [
                                { text: "MP3", value: "mp3" },
                                { text: "M4A / AAC", value: "aac" },
                                { text: "Opus", value: "opus" },
                                { text: "FLAC", value: "flac" },
                                { text: "WAV", value: "wav" }
                            ]
                            onActivated: function(idx, val) { settingsController.set("audio_codec", val) }
                        }

                        ModernDropdown {
                            label: "Audio Bitrate"
                            currentValue: String(settingsController.get("audio_quality") || "192")
                            model: [
                                { text: "320 kbps", value: "320" },
                                { text: "256 kbps", value: "256" },
                                { text: "192 kbps", value: "192" },
                                { text: "128 kbps", value: "128" },
                                { text: "96 kbps", value: "96" }
                            ]
                            onActivated: function(idx, val) { settingsController.set("audio_quality", val) }
                        }
                    }

                    ModernTextField {
                        width: 440
                        label: "Filename Template"
                        text: settingsController.get("filename_template") || "%(title)s.%(ext)s"
                        onTextEdited: settingsController.set("filename_template", text)
                    }
                }

                // ════════════════ TAB 3: PLAYLIST & QUEUE ════════════════
                Column {
                    visible: root.activeTab === 3
                    width: parent.width
                    spacing: 16

                    Text { text: "Playlist & Queue Settings"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    ModernDropdown {
                        label: "Max Concurrent Downloads"
                        currentValue: String(settingsController.get("max_concurrent_downloads") || "3")
                        model: ["1", "2", "3", "4", "5", "6", "8", "10"]
                        onActivated: function(idx, val) { settingsController.set("max_concurrent_downloads", parseInt(val)) }
                    }

                    ModernSwitch {
                        text: "Create subfolder for Playlist"
                        checked: settingsController.get("create_playlist_folder") !== false
                        onToggled: function(val) { settingsController.set("create_playlist_folder", val) }
                    }

                    ModernTextField {
                        width: 440
                        label: "Playlist Filename Format"
                        text: settingsController.get("playlist_filename_template") || "%(playlist_index)s - %(title)s.%(ext)s"
                        onTextEdited: settingsController.set("playlist_filename_template", text)
                    }
                }

                // ════════════════ TAB 4: ADVANCED ════════════════
                Column {
                    visible: root.activeTab === 4
                    width: parent.width
                    spacing: 16

                    Text { text: "Hardware Acceleration"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    ModernDropdown {
                        label: "FFmpeg GPU Acceleration"
                        currentValue: settingsController.get("hw_accel") || "auto"
                        model: [
                            { text: "Disabled", value: "none" },
                            { text: "Auto (Recommended)", value: "auto" },
                            { text: "NVIDIA (CUDA)", value: "cuda" },
                            { text: "Intel (QSV)", value: "qsv" },
                            { text: "AMD / Generic (D3D11VA)", value: "d3d11va" }
                        ]
                        onActivated: function(idx, val) { settingsController.set("hw_accel", val) }
                    }

                    Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                    Text { text: "Authentication & Cookies"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    ModernDropdown {
                        label: "Import Browser Cookies"
                        currentValue: settingsController.get("browser_cookies") || "none"
                        model: ["none", "chrome", "edge", "firefox", "brave", "opera", "vivaldi", "safari"]
                        onActivated: function(idx, val) { settingsController.set("browser_cookies", val) }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        ModernTextField {
                            id: cookiesPathField
                            width: parent.width - 100
                            label: "Cookies File (Optional)"
                            text: settingsController.get("cookies_path") || ""
                            readOnly: true
                        }

                        ModernButton {
                            text: "Browse"
                            variant: "secondary"
                            customHeight: 42
                            anchors.bottom: cookiesPathField.bottom
                            onClicked: {
                                var res = settingsController.browseFile("Select Cookies File", "Text Files (*.txt);;All Files (*.*)")
                                if (res !== "") {
                                    cookiesPathField.text = res
                                    settingsController.set("cookies_path", res)
                                }
                            }
                        }
                    }

                    Text { text: "Or login via embedded browser to capture cookies:"; font.pixelSize: 12; color: appController.textSecondaryColor }

                    Row {
                        spacing: 10
                        ModernButton { text: "Login to YouTube"; variant: "secondary"; onClicked: settingsController.openBrowserLogin("https://www.youtube.com/") }
                        ModernButton { text: "Login to Instagram"; variant: "secondary"; onClicked: settingsController.openBrowserLogin("https://www.instagram.com/") }
                        ModernButton { text: "Login to Facebook"; variant: "secondary"; onClicked: settingsController.openBrowserLogin("https://www.facebook.com/") }
                        ModernButton { text: "Login to X (Twitter)"; variant: "secondary"; onClicked: settingsController.openBrowserLogin("https://x.com/") }
                    }

                    Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                    Text { text: "Backend Engines & Updates"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    Row {
                        spacing: 12

                        ModernDropdown {
                            label: "Update Check Frequency"
                            currentValue: settingsController.get("engine_update_interval") || "weekly"
                            model: [
                                { text: "Daily", value: "daily" },
                                { text: "Weekly", value: "weekly" },
                                { text: "Monthly", value: "monthly" },
                                { text: "Never", value: "never" }
                            ]
                            onActivated: function(idx, val) { settingsController.set("engine_update_interval", val) }
                        }

                        ModernButton {
                            text: "Check Updates"
                            variant: "outlined"
                            anchors.bottom: parent.bottom
                            onClicked: settingsController.checkForEngineUpdates()
                        }

                        ModernButton {
                            text: "Update Engines Now"
                            variant: "primary"
                            anchors.bottom: parent.bottom
                            onClicked: settingsController.updateEnginesNow()
                        }
                    }

                    // Engine version tags
                    Rectangle {
                        width: parent.width
                        height: 48
                        radius: 8
                        color: appController.surfaceVariantColor

                        Row {
                            anchors.centerIn: parent
                            spacing: 24

                            Repeater {
                                model: ["yt-dlp", "spotdl", "curl_cffi"]
                                delegate: Row {
                                    spacing: 6
                                    Text { text: modelData + ":"; font.pixelSize: 12; font.weight: Font.Bold; color: appController.primaryColor }
                                    Text {
                                        text: {
                                            if (root.engineStatus && root.engineStatus.engines && root.engineStatus.engines[modelData]) {
                                                return root.engineStatus.engines[modelData].current
                                            }
                                            return "Installed"
                                        }
                                        font.pixelSize: 12
                                        color: appController.textSecondaryColor
                                    }
                                }
                            }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                    Text { text: "Developer Mode"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    ModernSwitch {
                        text: "Enable Developer Mode"
                        subtitle: "Unlocks Troubleshoot tab and deep system diagnostics"
                        checked: root.devMode
                        onToggled: function(val) {
                            root.devMode = val
                            settingsController.set("developer_mode", val)
                        }
                    }
                }

                // ════════════════ TAB 5: TROUBLESHOOT ════════════════
                Column {
                    visible: root.activeTab === 5 && root.devMode
                    width: parent.width
                    spacing: 16

                    Text { text: "System Diagnostics & Health"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    Row {
                        spacing: 10

                        ModernButton {
                            text: "Refresh Status"
                            variant: "outlined"
                            onClicked: settingsController.runTroubleshoot()
                        }

                        ModernButton {
                            text: "Fix Missing Dependencies"
                            variant: "primary"
                            onClicked: settingsController.fixDependencies()
                        }
                    }

                    // Diagnostics list
                    Rectangle {
                        width: parent.width
                        implicitHeight: diagCol.implicitHeight + 20
                        radius: 8
                        color: appController.surfaceVariantColor
                        border.width: 1
                        border.color: appController.borderColor

                        Column {
                            id: diagCol
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8

                            Repeater {
                                model: (root.troubleshootStatus && root.troubleshootStatus.items) ? root.troubleshootStatus.items : []
                                delegate: Row {
                                    spacing: 10
                                    Text {
                                        text: modelData.installed ? "✔" : "✖"
                                        color: modelData.installed ? appController.successColor : appController.errorColor
                                        font.pixelSize: 14
                                    }
                                    Text {
                                        text: modelData.name
                                        font.family: "Segoe UI, Inter, sans-serif"
                                        font.pixelSize: 13
                                        color: appController.textPrimaryColor
                                    }
                                }
                            }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                    Text { text: "Loaded System DLLs"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }

                    ModernButton {
                        text: "Load System DLLs"
                        variant: "secondary"
                        onClicked: settingsController.loadSystemDlls()
                    }

                    Rectangle {
                        width: parent.width
                        height: 180
                        radius: 8
                        color: "#080c16"
                        border.width: 1
                        border.color: appController.borderColor

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: 10
                            clip: true

                            TextArea {
                                text: root.dllOutput !== "" ? root.dllOutput : "Click 'Load System DLLs' to inspect loaded modules."
                                readOnly: true
                                color: "#94a3b8"
                                font.family: "Consolas, monospace"
                                font.pixelSize: 11
                                background: null
                            }
                        }
                    }
                }
            }
        }
    }
}

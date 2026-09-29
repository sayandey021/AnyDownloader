import QtQuick
import QtQuick.Controls
import "../components"

Popup {
    id: root

    property var info: null
    property bool isPlaylist: info ? ('entries' in info && info._type === 'playlist') : false
    property var selectedIndices: []
    property string downloadType: "Video"  // "Video", "Audio Only", "Image"
    property string selectedQuality: "best"
    property string selectedFormat: "mp4"
    property string selectedAudioCodec: "mp3"
    property string selectedAudioQuality: "192"
    property bool embedThumbnail: true
    property bool embedSubtitles: false
    property string subtitleLang: "en"
    property bool embedMetadata: true
    property bool embedChapters: true
    property bool enableSponsorblock: false
    property string saveLocation: ""

    signal startDownloadRequested(var options)
    signal downloadThumbnailRequested(var info)

    width: isPlaylist ? 920 : 800
    height: isPlaylist ? 620 : 560
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape

    background: Rectangle {
        radius: 16
        color: appController.surfaceColor
        border.width: 1
        border.color: appController.borderColor
    }

    onOpened: {
        initializeFromInfo()
    }

    function initializeFromInfo() {
        if (!info) return

        // Set default save location
        saveLocation = settingsController.get("default_download_path") || ""

        // Check if audio platform (Spotify, Apple Music, SoundCloud, Tidal, etc.)
        var extKey = (info.extractor_key || "").toLowerCase()
        var urlLower = (info.webpage_url || info.original_url || "").toLowerCase()
        var isAudioPlat = info._spotify || ["spotify", "soundcloud", "applemusic", "tidal", "deezer", "gaana", "lastfm"].indexOf(extKey) !== -1 || urlLower.indexOf("spotify.com") !== -1

        if (isAudioPlat) {
            downloadType = "Audio Only"
        } else {
            downloadType = "Video"
        }

        // Initialize playlist selection
        if (isPlaylist && info.entries) {
            var allIdx = []
            for (var i = 0; i < info.entries.length; i++) {
                allIdx.push(i)
            }
            selectedIndices = allIdx
        }

        // Defaults from settings
        embedThumbnail = settingsController.get("embed_thumbnail") !== false
        embedSubtitles = settingsController.get("embed_subtitles") === true
        subtitleLang = settingsController.get("auto_subtitle_lang") || "en"
        embedMetadata = settingsController.get("embed_metadata") !== false
        embedChapters = settingsController.get("embed_chapters") !== false
        enableSponsorblock = settingsController.get("enable_sponsorblock") === true
        selectedAudioCodec = settingsController.get("audio_codec") || "mp3"
        selectedAudioQuality = String(settingsController.get("audio_quality") || "192")
    }

    contentItem: Column {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // Dialog Title Header
        Row {
            width: parent.width
            spacing: 10

            Text {
                text: "⬇"
                font.pixelSize: 18
                color: appController.primaryColor
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: root.isPlaylist ? "Download Playlist" : "Download Media"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 18
                font.weight: Font.Bold
                color: appController.textPrimaryColor
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: appController.borderColor
        }

        // Two-Panel Body
        Row {
            width: parent.width
            height: parent.height - 110
            spacing: 20

            // ════════════════ LEFT PANEL ════════════════
            Column {
                width: root.isPlaylist ? 440 : 340
                height: parent.height
                spacing: 12

                // Single Media preview
                Column {
                    visible: !root.isPlaylist
                    width: parent.width
                    spacing: 10

                    Rectangle {
                        width: parent.width
                        height: 180
                        radius: 10
                        color: appController.surfaceVariantColor
                        clip: true

                        Image {
                            anchors.fill: parent
                            source: (root.info && root.info.thumbnail) ? root.info.thumbnail : ""
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                        }
                    }

                    Text {
                        width: parent.width
                        text: (root.info && (root.info.title || root.info.fulltitle)) ? (root.info.title || root.info.fulltitle) : "Unknown Media"
                        font.family: "Segoe UI, Inter, sans-serif"
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        color: appController.textPrimaryColor
                        elide: Text.ElideRight
                        maximumLineCount: 2
                        wrapMode: Text.Wrap
                    }

                    Text {
                        text: (root.info && (root.info.uploader || root.info.channel || root.info.creator)) ? (root.info.uploader || root.info.channel || root.info.creator) : ""
                        font.family: "Segoe UI, Inter, sans-serif"
                        font.pixelSize: 12
                        color: appController.textSecondaryColor
                    }
                }

                // Playlist preview & item list
                Column {
                    visible: root.isPlaylist
                    width: parent.width
                    height: parent.height
                    spacing: 8

                    Row {
                        width: parent.width
                        spacing: 12

                        Rectangle {
                            width: 100
                            height: 65
                            radius: 8
                            color: appController.surfaceVariantColor
                            clip: true

                            Image {
                                anchors.fill: parent
                                source: (root.info && root.info.thumbnail) ? root.info.thumbnail : ""
                                fillMode: Image.PreserveAspectCrop
                            }
                        }

                        Column {
                            width: parent.width - 112
                            spacing: 4

                            Text {
                                width: parent.width
                                text: root.info ? (root.info.title || "Playlist") : ""
                                font.family: "Segoe UI, Inter, sans-serif"
                                font.pixelSize: 14
                                font.weight: Font.Bold
                                color: appController.textPrimaryColor
                                elide: Text.ElideRight
                            }

                            Text {
                                text: root.info ? (root.info.uploader || "") : ""
                                font.pixelSize: 11
                                color: appController.textSecondaryColor
                            }

                            Text {
                                text: (root.info && root.info.entries ? root.info.entries.length : 0) + " items • " + root.selectedIndices.length + " selected"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                color: appController.accentCyanColor
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        ModernButton {
                            text: "Select All"
                            variant: "outlined"
                            customHeight: 28
                            onClicked: {
                                var all = []
                                for (var i = 0; i < (root.info && root.info.entries ? root.info.entries.length : 0); i++) all.push(i)
                                root.selectedIndices = all
                            }
                        }

                        ModernButton {
                            text: "Select None"
                            variant: "ghost"
                            customHeight: 28
                            onClicked: {
                                root.selectedIndices = []
                            }
                        }
                    }

                    // Playlist scroll list
                    Rectangle {
                        width: parent.width
                        height: parent.height - 130
                        radius: 8
                        color: appController.surfaceVariantColor
                        border.width: 1
                        border.color: appController.borderColor
                        clip: true

                        ListView {
                            id: plList
                            anchors.fill: parent
                            anchors.margins: 4
                            spacing: 2
                            model: (root.info && root.info.entries) ? root.info.entries : []
                            delegate: Rectangle {
                                width: plList.width
                                height: 38
                                radius: 6
                                color: plItemMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : "transparent"

                                property bool isItemChecked: root.selectedIndices.indexOf(index) !== -1

                                Row {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8
                                    spacing: 8

                                    CheckBox {
                                        checked: isItemChecked
                                        anchors.verticalCenter: parent.verticalCenter
                                        onToggled: {
                                            var current = root.selectedIndices.slice()
                                            var pos = current.indexOf(index)
                                            if (checked && pos === -1) current.push(index)
                                            else if (!checked && pos !== -1) current.splice(pos, 1)
                                            root.selectedIndices = current
                                        }
                                    }

                                    Text {
                                        text: (index + 1) + "."
                                        font.pixelSize: 11
                                        color: appController.textSecondaryColor
                                        anchors.verticalCenter: parent.verticalCenter
                                    }

                                    Text {
                                        width: parent.width - 90
                                        text: modelData.title || ("Item " + (index + 1))
                                        font.family: "Segoe UI, Inter, sans-serif"
                                        font.pixelSize: 12
                                        color: appController.textPrimaryColor
                                        elide: Text.ElideRight
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                MouseArea {
                                    id: plItemMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        var current = root.selectedIndices.slice()
                                        var pos = current.indexOf(index)
                                        if (pos === -1) current.push(index)
                                        else current.splice(pos, 1)
                                        root.selectedIndices = current
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                width: 1
                height: parent.height
                color: appController.borderColor
            }

            // ════════════════ RIGHT PANEL ════════════════
            ScrollView {
                width: parent.width - (root.isPlaylist ? 440 : 340) - 21
                height: parent.height
                clip: true

                Column {
                    width: parent.width - 12
                    spacing: 14

                    // Download Type Dropdown
                    ModernDropdown {
                        width: parent.width
                        label: "Download Type"
                        currentValue: root.downloadType
                        model: ["Video", "Audio Only"]
                        onActivated: function(idx, val) {
                            root.downloadType = val
                        }
                    }

                    // Format & Quality (Video Mode)
                    Column {
                        visible: root.downloadType === "Video"
                        width: parent.width
                        spacing: 12

                        ModernDropdown {
                            width: parent.width
                            label: "Video Quality"
                            currentValue: root.selectedQuality
                            model: [
                                { text: "Best Quality (Default)", value: "best" },
                                { text: "4320p (8K)", value: "4320" },
                                { text: "2160p (4K)", value: "2160" },
                                { text: "1440p (2K)", value: "1440" },
                                { text: "1080p (Full HD)", value: "1080" },
                                { text: "720p (HD)", value: "720" },
                                { text: "480p", value: "480" },
                                { text: "360p", value: "360" }
                            ]
                            onActivated: function(idx, val) { root.selectedQuality = val }
                        }

                        ModernDropdown {
                            width: parent.width
                            label: "Container / Format"
                            currentValue: root.selectedFormat
                            model: [
                                { text: "Original", value: "best" },
                                { text: "MP4 (Recommended)", value: "mp4" },
                                { text: "MKV", value: "mkv" },
                                { text: "WebM", value: "webm" },
                                { text: "AVI", value: "avi" },
                                { text: "MOV", value: "mov" }
                            ]
                            onActivated: function(idx, val) { root.selectedFormat = val }
                        }
                    }

                    // Format & Quality (Audio Mode)
                    Column {
                        visible: root.downloadType === "Audio Only"
                        width: parent.width
                        spacing: 12

                        ModernDropdown {
                            width: parent.width
                            label: "Audio Codec"
                            currentValue: root.selectedAudioCodec
                            model: [
                                { text: "MP3 (Universal)", value: "mp3" },
                                { text: "M4A / AAC", value: "m4a" },
                                { text: "FLAC (Lossless)", value: "flac" },
                                { text: "WAV (Uncompressed)", value: "wav" },
                                { text: "Opus", value: "opus" },
                                { text: "OGG", value: "ogg" }
                            ]
                            onActivated: function(idx, val) { root.selectedAudioCodec = val }
                        }

                        ModernDropdown {
                            width: parent.width
                            label: "Audio Quality (Bitrate)"
                            currentValue: root.selectedAudioQuality
                            model: [
                                { text: "320 kbps (High Quality)", value: "320" },
                                { text: "256 kbps", value: "256" },
                                { text: "192 kbps (Standard)", value: "192" },
                                { text: "128 kbps", value: "128" },
                                { text: "96 kbps", value: "96" },
                                { text: "64 kbps", value: "64" }
                            ]
                            onActivated: function(idx, val) { root.selectedAudioQuality = val }
                        }
                    }

                    // Embed Options Section
                    Text {
                        text: "Embed Options"
                        font.family: "Segoe UI, Inter, sans-serif"
                        font.pixelSize: 12
                        font.weight: Font.Bold
                        color: appController.accentCyanColor
                    }

                    ModernSwitch {
                        text: "Embed Thumbnail"
                        checked: root.embedThumbnail
                        onToggled: function(val) { root.embedThumbnail = val }
                    }

                    ModernSwitch {
                        text: "Embed Metadata (Title, Artist, Album)"
                        checked: root.embedMetadata
                        onToggled: function(val) { root.embedMetadata = val }
                    }

                    ModernSwitch {
                        text: "Save with Chapters"
                        checked: root.embedChapters
                        onToggled: function(val) { root.embedChapters = val }
                    }

                    ModernSwitch {
                        text: "Embed Subtitles"
                        checked: root.embedSubtitles
                        onToggled: function(val) { root.embedSubtitles = val }
                    }

                    ModernSwitch {
                        text: "SponsorBlock (YouTube)"
                        subtitle: "Cut sponsors, promos, and intros"
                        checked: root.enableSponsorblock
                        onToggled: function(val) { root.enableSponsorblock = val }
                    }

                    // Save Location
                    Text {
                        text: "Download Folder"
                        font.family: "Segoe UI, Inter, sans-serif"
                        font.pixelSize: 12
                        font.weight: Font.Bold
                        color: appController.accentCyanColor
                    }

                    Row {
                        width: parent.width
                        spacing: 8

                        ModernTextField {
                            width: parent.width - 90
                            text: root.saveLocation
                            readOnly: true
                        }

                        ModernButton {
                            text: "Browse"
                            variant: "secondary"
                            customHeight: 42
                            onClicked: {
                                var folder = settingsController.browseFolder(root.saveLocation)
                                if (folder !== "") root.saveLocation = folder
                            }
                        }
                    }
                }
            }
        }

        // Bottom Action Buttons
        Row {
            anchors.right: parent.right
            spacing: 12

            ModernButton {
                text: "Cancel"
                variant: "ghost"
                onClicked: root.close()
            }

            ModernButton {
                text: "Thumbnail"
                variant: "outlined"
                onClicked: {
                    root.close()
                    root.downloadThumbnailRequested(root.info)
                }
            }

            ModernButton {
                text: (root.info && root.info.is_live) ? "Record Stream" : "Download"
                variant: "primary"
                onClicked: {
                    root.close()
                    var isAud = root.downloadType === "Audio Only"
                    var formatId = "best"
                    if (isAud) {
                        formatId = "bestaudio/best"
                    } else if (root.selectedQuality !== "best") {
                        formatId = "bestvideo[height<=" + root.selectedQuality + "]+bestaudio/best"
                    }

                    var dlOpts = {
                        info: root.info,
                        is_audio: isAud,
                        format_id: formatId,
                        video_ext: root.selectedFormat,
                        audio_codec: root.selectedAudioCodec,
                        audio_quality: root.selectedAudioQuality,
                        embed_thumbnail: root.embedThumbnail,
                        embed_subtitles: root.embedSubtitles,
                        subtitle_lang: root.subtitleLang,
                        embed_metadata: root.embedMetadata,
                        embed_chapters: root.embedChapters,
                        enable_sponsorblock: root.enableSponsorblock,
                        output_path: root.saveLocation,
                        selected_entries: root.isPlaylist ? root.selectedIndices : null
                    }
                    root.startDownloadRequested(dlOpts)
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import "../components"

Popup {
    id: root

    width: 650
    height: 540
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape

    background: Rectangle {
        radius: 14
        color: appController.surfaceColor
        border.width: 1
        border.color: appController.borderColor
    }

    contentItem: Column {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

        Row {
            spacing: 10

            Text {
                text: "🌐"
                font.pixelSize: 20
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "Supported Sites"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 18
                font.weight: Font.Bold
                color: appController.textPrimaryColor
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Text {
            width: parent.width
            text: "Any Downloader natively supports fetching from 1000+ websites. Here are some popular ones:"
            font.family: "Segoe UI, Inter, sans-serif"
            font.pixelSize: 13
            color: appController.textSecondaryColor
            wrapMode: Text.Wrap
        }

        Rectangle {
            width: parent.width
            height: 1
            color: appController.borderColor
        }

        ScrollView {
            width: parent.width
            height: parent.height - 160
            clip: true

            Column {
                width: parent.width - 12
                spacing: 16

                Repeater {
                    model: [
                        {
                            category: "Video & Streaming",
                            sites: ["YouTube", "Twitch", "Vimeo", "Dailymotion", "Trovo"]
                        },
                        {
                            category: "Music & Audio",
                            sites: ["Spotify", "Apple Music", "SoundCloud", "YT Music", "Tidal", "Deezer", "JioSaavn", "Gaana", "Last.fm", "Bandcamp"]
                        },
                        {
                            category: "Social Media",
                            sites: ["Instagram", "Twitter / X", "Facebook", "TikTok", "Reddit", "LinkedIn", "Snapchat", "Patreon", "Bluesky", "VK"]
                        },
                        {
                            category: "Images & Art",
                            sites: ["Pinterest", "Tumblr", "ArtStation", "DeviantArt", "Behance", "Imgur", "Wallpaper Cave", "Danbooru", "Wallhaven", "Tenor"]
                        },
                        {
                            category: "Anime & Manga",
                            sites: ["9Anime", "MangaDex", "Webtoon", "Tapas", "MangaFire", "MangaRead", "Rawkuma", "Dynasty Reader", "WeebCentral"]
                        },
                        {
                            category: "Adult / NSFW",
                            sites: ["Pornhub", "XVideos", "XNXX", "xhamster", "xozilla", "vikiporn", "pornpics", "HentaiHere", "nHentai"]
                        }
                    ]

                    delegate: Column {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: modelData.category
                            font.family: "Segoe UI, Inter, sans-serif"
                            font.pixelSize: 14
                            font.weight: Font.Bold
                            color: appController.primaryColor
                        }

                        Flow {
                            width: parent.width
                            spacing: 8

                            Repeater {
                                model: modelData.sites
                                delegate: Rectangle {
                                    height: 30
                                    width: siteNameText.implicitWidth + 20
                                    radius: 6
                                    color: appController.surfaceVariantColor

                                    Text {
                                        id: siteNameText
                                        anchors.centerIn: parent
                                        text: modelData
                                        font.family: "Segoe UI, Inter, sans-serif"
                                        font.pixelSize: 12
                                        font.weight: Font.Medium
                                        color: appController.textPrimaryColor
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Row {
            width: parent.width
            spacing: 12

            ModernButton {
                text: "View all 1000+ sites"
                variant: "outlined"
                onClicked: Qt.openUrlExternally("https://github.com/sayandey021/AnyDownloader/blob/main/docs/SUPPORTED_SITES.md")
            }

            Item { width: Math.max(0, parent.width - 240); height: 1 }

            ModernButton {
                text: "Close"
                variant: "primary"
                onClicked: root.close()
            }
        }
    }
}

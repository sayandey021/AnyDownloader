import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"
import "dialogs"

ApplicationWindow {
    id: mainWindow
    visible: true
    width: 960
    height: 700
    minimumWidth: 840
    minimumHeight: 600
    title: "Any Downloader"
    flags: Qt.Window | Qt.FramelessWindowHint

    color: appController.backgroundColor

    property bool isSetupMode: false

    Component.onCompleted: {
        appController.set_window(mainWindow)
    }

    Connections {
        target: appController
        function onToastRequested(msg, type) {
            toast.show(msg, type)
        }
        function onCloseDialogRequested() {
            closeConfirmDialog.open()
        }
        function onWindowActivateRequested() {
            mainWindow.show()
            mainWindow.raise()
            mainWindow.requestActivate()
        }
    }

    // Background Image Overlay
    Image {
        id: bgOverlay
        anchors.fill: parent
        source: {
            if (!appController.bgImagePath) return ""
            if (appController.bgImagePath.indexOf("/") === 0) {
                return "file:///" + applicationDirPath + "/assets" + appController.bgImagePath
            }
            if (appController.bgImagePath.indexOf(":") !== -1) {
                return "file:///" + appController.bgImagePath
            }
            return appController.bgImagePath
        }
        fillMode: Image.PreserveAspectCrop
        opacity: appController.bgImageOpacity
        visible: appController.bgImagePath !== ""
    }

    Column {
        anchors.fill: parent
        spacing: 0

        // Custom Frameless Title Bar
        CustomTitleBar {
            id: titleBar
            width: parent.width
        }

        // Main Body Layout
        Item {
            width: parent.width
            height: parent.height - titleBar.height

            // If setup mode is active (downloading FFmpeg)
            SetupPage {
                id: setupPage
                anchors.fill: parent
                visible: mainWindow.isSetupMode
                onSetupCompleted: {
                    mainWindow.isSetupMode = false
                }
            }

            // Normal Application View
            Row {
                anchors.fill: parent
                visible: !mainWindow.isSetupMode
                spacing: 0

                // Navigation Sidebar
                Sidebar {
                    id: sidebar
                    height: parent.height
                }

                // Page Views Container
                Item {
                    id: pageContainer
                    width: parent.width - sidebar.width
                    height: parent.height
                    clip: true

                    SearchPage {
                        id: searchPage
                        anchors.fill: parent
                        visible: appController.currentPage === 0
                        onOpenSupportedSitesRequested: supportedSitesDialog.open()
                    }

                    HistoryPage {
                        id: historyPage
                        anchors.fill: parent
                        visible: appController.currentPage === 1
                        onSearchAgainRequested: function(url) {
                            appController.setPage(0)
                            searchPage.doSearch(url)
                        }
                        onRedownloadRequested: function(rData) {
                            fetchDialog.info = rData.info || rData
                            fetchDialog.open()
                        }
                    }

                    DownloadsPage {
                        id: downloadsPage
                        anchors.fill: parent
                        visible: appController.currentPage === 2
                        onOpenLogsRequested: function(taskId, title, logText) {
                            logsDialog.taskId = taskId
                            logsDialog.itemTitle = title
                            logsDialog.logContent = logText
                            logsDialog.open()
                        }
                        onRedownloadRequested: function(infoMap) {
                            fetchDialog.info = infoMap
                            fetchDialog.open()
                        }
                        onDeleteRequested: function(taskId, title, finalFilepath) {
                            deleteConfirmDialog.taskId = taskId
                            deleteConfirmDialog.itemTitle = title
                            deleteConfirmDialog.finalFilepath = finalFilepath
                            deleteConfirmDialog.deleteFileFromDisk = false
                            deleteConfirmDialog.open()
                        }
                    }

                    SettingsPage {
                        id: settingsPage
                        anchors.fill: parent
                        visible: appController.currentPage === 3
                    }

                    AboutPage {
                        id: aboutPage
                        anchors.fill: parent
                        visible: appController.currentPage === 4
                        onOpenVersionHistoryRequested: versionHistoryDialog.open()
                    }
                }
            }
        }
    }

    // Modal Dialogs
    FetchDialog {
        id: fetchDialog
        onStartDownloadRequested: function(opts) {
            downloaderController.startDownload(opts)
            appController.setPage(2)  // switch to Downloads page
            appController.showToast("Download started!", "success")
        }
        onDownloadThumbnailRequested: function(info) {
            var thumbUrl = info.thumbnail
            if (!thumbUrl && info.thumbnails) thumbUrl = info.thumbnails[info.thumbnails.length - 1].url
            if (thumbUrl) {
                var opts = {
                    info: info,
                    is_audio: false,
                    is_thumbnail: true,
                    format_id: "best",
                    output_path: settingsController.get("default_download_path")
                }
                downloaderController.startDownload(opts)
                appController.setPage(2)
                appController.showToast("Downloading thumbnail...", "info")
            }
        }
    }

    LogsDialog {
        id: logsDialog
    }

    CloseConfirmDialog {
        id: closeConfirmDialog
    }

    DeleteConfirmDialog {
        id: deleteConfirmDialog
    }

    SupportedSitesDialog {
        id: supportedSitesDialog
    }

    VersionHistoryDialog {
        id: versionHistoryDialog
    }

    // Toast Floating Alert
    Toast {
        id: toast
    }
}

using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;

class FletLauncher {
    [DllImport("user32.dll", SetLastError = true)]
    static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

    [DllImport("user32.dll")]
    static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    static extern bool BringWindowToTop(IntPtr hWnd);

    [DllImport("user32.dll")]
    static extern bool IsIconic(IntPtr hWnd);

    [DllImport("kernel32.dll")]
    static extern uint GetCurrentThreadId();

    [DllImport("user32.dll")]
    static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);

    [DllImport("user32.dll")]
    static extern IntPtr SetFocus(IntPtr hWnd);

    static void RestoreAndFocus(IntPtr hwnd) {
        if (hwnd == IntPtr.Zero) return;

        if (IsIconic(hwnd)) {
            ShowWindow(hwnd, 9); // SW_RESTORE
        } else {
            ShowWindow(hwnd, 5); // SW_SHOW
        }

        uint curThread = GetCurrentThreadId();
        IntPtr fgHwnd = GetForegroundWindow();
        uint dummy;
        uint fgThread = fgHwnd != IntPtr.Zero ? GetWindowThreadProcessId(fgHwnd, out dummy) : 0;
        uint appThread = GetWindowThreadProcessId(hwnd, out dummy);

        if (fgThread != 0 && fgThread != curThread) AttachThreadInput(curThread, fgThread, true);
        if (appThread != 0 && appThread != curThread) AttachThreadInput(curThread, appThread, true);

        SetForegroundWindow(hwnd);
        BringWindowToTop(hwnd);
        SetFocus(hwnd);

        if (appThread != 0 && appThread != curThread) AttachThreadInput(curThread, appThread, false);
        if (fgThread != 0 && fgThread != curThread) AttachThreadInput(curThread, fgThread, false);
    }

    static void TrySendIpcActivate() {
        try {
            string portFile = Path.Combine(Path.GetTempPath(), "any_downloader_app.port");
            if (File.Exists(portFile)) {
                string text = File.ReadAllText(portFile).Trim();
                int port;
                if (int.TryParse(text, out port)) {
                    using (var client = new TcpClient()) {
                        client.Connect("127.0.0.1", port);
                        byte[] msg = Encoding.UTF8.GetBytes("activate\n");
                        client.GetStream().Write(msg, 0, msg.Length);
                    }
                }
            }
        } catch { }
    }

    static int Main(string[] args) {
        // If launched with arguments by Python/Flet, forward to real Flutter runner
        bool hasFletArgs = args.Length >= 2 || (args.Length == 1 && (
            args[0].StartsWith("http") || 
            args[0].StartsWith("tcp") || 
            args[0].StartsWith("ws") || 
            args[0].IndexOf("pipe", StringComparison.OrdinalIgnoreCase) >= 0
        ));

        if (hasFletArgs) {
            string dir = AppDomain.CurrentDomain.BaseDirectory;
            string realExe = Path.Combine(dir, "flet_bin.exe");
            if (!File.Exists(realExe)) {
                return 1;
            }

            var sb = new StringBuilder();
            for (int i = 0; i < args.Length; i++) {
                if (i > 0) sb.Append(' ');
                string a = args[i];
                if (string.IsNullOrEmpty(a)) {
                    sb.Append("\"\"");
                } else if (a.IndexOf(' ') >= 0 || a.IndexOf('\"') >= 0 || a.IndexOf('\t') >= 0) {
                    sb.Append('\"').Append(a.Replace("\"", "\\\"")).Append('\"');
                } else {
                    sb.Append(a);
                }
            }

            var psi = new ProcessStartInfo(realExe, sb.ToString()) {
                UseShellExecute = false
            };
            try {
                var proc = Process.Start(psi);
                proc.WaitForExit();
                return proc.ExitCode;
            } catch {
                return 1;
            }
        }

        // Flet.exe was launched with NO arguments (e.g. clicked from taskbar jump list menu)!
        // 1. Notify primary Python instance via IPC
        TrySendIpcActivate();

        // 2. Restore and focus native window
        IntPtr hwnd = FindWindow("FLUTTER_RUNNER_WIN32_WINDOW", "Any Downloader");
        if (hwnd == IntPtr.Zero) {
            hwnd = FindWindow(null, "Any Downloader");
        }
        if (hwnd == IntPtr.Zero) {
            hwnd = FindWindow("FLUTTER_RUNNER_WIN32_WINDOW", null);
        }
        if (hwnd != IntPtr.Zero) {
            RestoreAndFocus(hwnd);
            return 0;
        }

        // 3. If window not found, try to launch the main app via MSIX package AUMID
        try {
            Process.Start("explorer.exe", "shell:AppsFolder\\Saayan.AnyDownloader_f0v6x7d2rzc78!AnyDownloader");
        } catch { }

        return 0;
    }
}

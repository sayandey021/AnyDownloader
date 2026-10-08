# Any Downloader - Free Google Apps Script Bug Report Webhook Setup

This guide explains how to deploy the serverless bug report receiver for **Any Downloader** in **under 2 minutes** using Google Apps Script.

---

## 🚀 Email Routing Architecture
- **Public Brand in App**: `saayanstudiosoft@gmail.com` (shown in dialogs, error fallbacks, and mailto links).
- **Sender Account**: `saayanstudiosoft@gmail.com` (runs the serverless Google Apps Script).
- **Recipient Inbox**: `sayandey021@gmail.com` (receives incoming bug report notifications immediately with native push alerts).
- **Reply-To Support**: If the user enters their contact email, clicking **Reply** in Gmail responds directly to that user.
- **100% Free**: No recurring third-party subscriptions or backend hosting required.

---

## 🛠️ Step-by-Step Deployment (2 Minutes)

### Step 1: Open Google Apps Script
1. Go to [https://script.google.com](https://script.google.com) in your browser.
2. Sign in with `saayanstudiosoft@gmail.com` (or your preferred Google account).
3. Click the **+ New project** button in the top left.

### Step 2: Paste the Webhook Code
1. Rename the project from *Untitled project* to **AnyDownloader-BugReport** (click the title at the top).
2. Delete any existing code in the `Code.gs` editor.
3. Open [`scripts/google_apps_script.js`](../scripts/google_apps_script.js) in your repository, copy all the code, and paste it into `Code.gs`.
4. Click the **Save** icon (disk icon) or press `Ctrl + S`.

### Step 3: Deploy as a Web App
1. Click the blue **Deploy** button in the top-right corner, and select **New deployment**.
2. Click the gear icon (**Select type**) next to *Select type* and choose **Web app**.
3. Configure the settings:
   - **Description**: `Any Downloader Bug Reporter`
   - **Execute as**: `Me (saayanstudiosoft@gmail.com)`
   - **Who has access**: `Anyone` *(Crucial: allows Any Downloader clients to post without requiring Google login)*
4. Click **Deploy**.
5. Google will ask you to **Authorize access**:
   - Click *Authorize access*.
   - Choose your account.
   - If you see *Google hasn't verified this app*, click **Advanced** -> **Go to AnyDownloader-BugReport (unsafe)** -> **Allow**.
6. Google will provide a **Web app URL** that looks like:
   ```text
   https://script.google.com/macros/s/AKfycb.../exec
   ```
7. Copy this URL.

### Step 4: Configure in Any Downloader
You have two easy ways to set your URL:

1. **Option A (In-App Settings)**:
   - Open Any Downloader -> **Settings** -> **Troubleshoot / Developer Mode**.
   - Paste the Webhook URL into the **Bug Report Webhook URL** field and click **Save**.
2. **Option B (Code Default)**:
   - Open [`src/backend/bug_report.py`](../src/backend/bug_report.py).
   - Set `DEFAULT_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycb.../exec"`.

---

## 🔒 Privacy & Transparency
- The in-app form displays an expandable **"View Diagnostic Data & Logs"** panel before sending.
- Only non-sensitive system info (OS, version, engine status) and the last 50 lines of logs are gathered.
- Sensitive tokens or cookies are **never** included.
- Offline fallback: If no internet is available, users can copy the full markdown report to their clipboard with 1 click.

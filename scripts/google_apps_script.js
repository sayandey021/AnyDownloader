/**
 * Any Downloader - Clean Structured Bug Reporter (Google Apps Script)
 * Sender Account (Execute As): saayanstudiosoft@gmail.com
 * Target Recipient Inbox: sayandey021@gmail.com
 * Public App Brand: saayanstudiosoft@gmail.com
 *
 * HOW TO DEPLOY:
 * 1. Open https://script.google.com logged into saayanstudiosoft@gmail.com.
 * 2. Paste this code into Code.gs.
 * 3. Click Save (Ctrl + S).
 * 4. Deploy -> Manage deployments -> Edit (Pencil icon) -> Version: "New version" -> Deploy.
 */

// Target inbox that receives incoming notifications
const TARGET_EMAIL = "sayandey021@gmail.com";

// Public developer email shown in the app & client responses
const PUBLIC_DEV_EMAIL = "saayanstudiosoft@gmail.com";

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return respondJson({ status: "error", message: "No post data received" }, 400);
    }

    var data = JSON.parse(e.postData.contents);

    var title = (data.title || "Bug Report").trim();
    var category = (data.category || "General Issue").trim();
    var userEmail = (data.user_email || "").trim();
    var description = (data.description || "No description provided.").trim();
    var appVersion = (data.app_version || "1.9.6").trim();
    var timestamp = data.timestamp || new Date().toISOString();
    var systemInfo = data.system_info || {};
    var logs = (data.logs || "No debug logs attached.").trim();

    var emailSubject = "[Any Downloader v" + appVersion + "] [" + category + "] " + title;

    // Perfectly aligned 2-column clean layout
    var htmlContent = buildAlignedHtml({
      title: title,
      category: category,
      userEmail: userEmail,
      description: description,
      appVersion: appVersion,
      timestamp: timestamp,
      systemInfo: systemInfo,
      logs: logs
    });

    var plainContent = buildPlainText({
      title: title,
      category: category,
      userEmail: userEmail,
      description: description,
      appVersion: appVersion,
      timestamp: timestamp,
      systemInfo: systemInfo,
      logs: logs
    });

    var emailOptions = {
      name: "Any Downloader Bug Reporter",
      htmlBody: htmlContent
    };

    if (userEmail && userEmail.indexOf("@") !== -1) {
      emailOptions.replyTo = userEmail;
    }

    try {
      GmailApp.sendEmail(TARGET_EMAIL, emailSubject, plainContent, emailOptions);
    } catch (err1) {
      emailOptions.to = TARGET_EMAIL;
      emailOptions.subject = emailSubject;
      emailOptions.body = plainContent;
      MailApp.sendEmail(emailOptions);
    }

    return respondJson({
      status: "success",
      message: "Bug report delivered successfully to " + PUBLIC_DEV_EMAIL
    });

  } catch (err) {
    return respondJson({
      status: "error",
      message: err.toString()
    }, 500);
  }
}

function doOptions(e) {
  return respondJson({ status: "ok" });
}

function respondJson(data, statusCode) {
  var output = ContentService.createTextOutput(JSON.stringify(data));
  output.setMimeType(ContentService.MimeType.JSON);
  return output;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function buildAlignedHtml(params) {
  var reporter = params.userEmail ?
    "<a href='mailto:" + escapeHtml(params.userEmail) + "' style='color: #2563eb; text-decoration: underline;'>" + escapeHtml(params.userEmail) + "</a> (Reply-To enabled)" :
    "Not provided (Anonymous)";

  var overviewRows = [
    ["Application", "Any Downloader v" + escapeHtml(params.appVersion)],
    ["Issue Category", escapeHtml(params.category)],
    ["Issue Title", escapeHtml(params.title)],
    ["Reported By", reporter],
    ["Timestamp", escapeHtml(params.timestamp)]
  ];

  var overviewTable = renderTable(overviewRows);

  var sysRows = [];
  for (var key in params.systemInfo) {
    sysRows.push([key, escapeHtml(params.systemInfo[key])]);
  }
  var sysTable = renderTable(sysRows);

  var descHtml = escapeHtml(params.description).replace(/\n/g, "<br>");
  var logsHtml = escapeHtml(params.logs);

  return `
  <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 13px; color: #1e293b; line-height: 1.6; max-width: 720px; padding: 6px 0;">
    
    <div style="font-weight: 700; font-size: 13px; color: #0f172a; margin-bottom: 4px; letter-spacing: 0.5px;">[OVERVIEW]</div>
    <div style="border-top: 1px dashed #cbd5e1; margin-bottom: 8px;"></div>
    ${overviewTable}

    <div style="font-weight: 700; font-size: 13px; color: #0f172a; margin-top: 18px; margin-bottom: 4px; letter-spacing: 0.5px;">[DESCRIPTION]</div>
    <div style="border-top: 1px dashed #cbd5e1; margin-bottom: 8px;"></div>
    <div style="padding: 4px 0 10px 0; color: #0f172a;">
      ${descHtml}
    </div>

    <div style="font-weight: 700; font-size: 13px; color: #0f172a; margin-top: 18px; margin-bottom: 4px; letter-spacing: 0.5px;">[SYSTEM DIAGNOSTICS]</div>
    <div style="border-top: 1px dashed #cbd5e1; margin-bottom: 8px;"></div>
    ${sysTable}

    <div style="font-weight: 700; font-size: 13px; color: #0f172a; margin-top: 18px; margin-bottom: 4px; letter-spacing: 0.5px;">[DEBUG LOGS — LAST 50 LINES]</div>
    <div style="border-top: 1px dashed #cbd5e1; margin-bottom: 8px;"></div>
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; overflow-x: auto; margin-top: 6px;">
      <pre style="margin: 0; font-family: Consolas, 'Courier New', monospace; font-size: 12px; color: #334155; line-height: 1.5; white-space: pre-wrap; word-break: break-all;">${logsHtml}</pre>
    </div>

    <div style="border-top: 1px solid #e2e8f0; margin-top: 24px; padding-top: 10px; font-size: 11px; color: #94a3b8;">
      Any Downloader Bug Dispatcher • Dispatched to ${TARGET_EMAIL} via ${PUBLIC_DEV_EMAIL}
    </div>

  </div>
  `;
}

function renderTable(rows) {
  if (!rows || rows.length === 0) {
    return "<div style='color: #64748b; padding: 4px 0;'>None provided</div>";
  }

  var html = "<table style='border-collapse: collapse; width: auto; font-size: 13px; line-height: 1.5;'>";
  for (var i = 0; i < rows.length; i++) {
    var label = rows[i][0];
    var val = rows[i][1];
    html += "<tr>" +
      "<td style='padding: 2px 24px 2px 0; vertical-align: top; color: #0f172a; font-weight: 600; white-space: nowrap;'>• " + label + ":</td>" +
      "<td style='padding: 2px 0; vertical-align: top; color: #334155;'>" + val + "</td>" +
      "</tr>";
  }
  html += "</table>";
  return html;
}

function buildPlainText(params) {
  var reporter = params.userEmail ? params.userEmail + " (Reply-To enabled)" : "Not provided (Anonymous)";

  var sysLines = [];
  for (var key in params.systemInfo) {
    sysLines.push("• " + key + ": " + params.systemInfo[key]);
  }

  return [
    "[OVERVIEW]",
    "• Application: Any Downloader v" + params.appVersion,
    "• Issue Category: " + params.category,
    "• Issue Title: " + params.title,
    "• Reported By: " + reporter,
    "• Timestamp: " + params.timestamp,
    "",
    "----------------------------------------------------------------------",
    "[DESCRIPTION]",
    "----------------------------------------------------------------------",
    params.description,
    "",
    "----------------------------------------------------------------------",
    "[SYSTEM DIAGNOSTICS]",
    "----------------------------------------------------------------------",
    sysLines.join("\n"),
    "",
    "----------------------------------------------------------------------",
    "[DEBUG LOGS — LAST 50 LINES]",
    "----------------------------------------------------------------------",
    params.logs,
    "",
    "----------------------------------------------------------------------",
    "Dispatched to " + TARGET_EMAIL + " via " + PUBLIC_DEV_EMAIL
  ].join("\n");
}

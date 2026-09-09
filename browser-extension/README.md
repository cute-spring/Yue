# Yue Browser Companion

This unpacked Chrome/Chromium extension explicitly shares the current HTTP/S tab's visible text with a local Yue backend. It is the P0 connection layer for browser collaboration; it is intentionally read-only.

## Install for development

1. Start the Yue backend on `http://127.0.0.1:8003`.
2. Open `chrome://extensions`, enable **Developer mode**, and select **Load unpacked**.
3. Choose this `browser-extension` directory.
4. Open the page you want to share, use the Yue Browser Companion toolbar button, then choose **Share current tab**.

The extension registers one ephemeral browser session and uploads the current visible-text snapshot. A Yue backend restart, a user disconnect, or an extension re-authorisation creates a new session.

## Privacy boundary

- The extension transmits page content only after the user presses **Share current tab**.
- It strips scripts, styles, and password inputs before making the snapshot.
- Yue does not persist the extension token, passwords, cookies, or MFA values in public session APIs.
- It does not click, fill, submit, navigate, or download anything in this milestone.

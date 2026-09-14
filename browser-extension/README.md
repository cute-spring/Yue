# Yue Browser Companion

This unpacked Chrome/Chromium extension explicitly shares the current HTTP/S tab's visible text with a local Yue backend. It is the connection layer for the controlled-write Beta of browser collaboration.

## Install for development

1. Start the Yue backend on `http://127.0.0.1:8003`.
2. Open `chrome://extensions`, enable **Developer mode**, and select **Load unpacked**.
3. Choose this `browser-extension` directory.
4. Open the page you want to share, use the Yue Browser Companion toolbar button, then choose **Share current tab**.

The extension registers one ephemeral browser session and uploads the current visible-text snapshot. A Yue backend restart, a user disconnect, or an extension re-authorisation creates a new session.

In this Beta, Yue asks for an explicit, per-command confirmation before every form change, save, submit, download, or navigation. A command that loses its browser response is marked for reconciliation and is never retried automatically.

## Privacy boundary

- The extension transmits page content only after the user presses **Share current tab**.
- It strips scripts, styles, and password inputs before making the snapshot.
- Yue does not persist the extension token, passwords, cookies, or MFA values in public session APIs.
- It keeps a local redacted command record; form values are not written to that record.
- It does not execute a save, submit, download, or navigation without a fresh explicit approval.
- It never automatically retries a command whose outcome is uncertain.

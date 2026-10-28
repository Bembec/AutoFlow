# Connect your Gmail

Luphina uses two kinds of email connection:

- **Email (SMTP)**: to *send* replies, invoices and reminders from your address.
- **Incoming email (IMAP)**: to *read* new emails, for example supplier invoices.

Gmail needs an **app password** for both. This is a separate 16-character password just for Luphina, which you can revoke at any time without changing your normal password.

## 1. Create an app password

1. Turn on **2-Step Verification** for your Google account (Google Account → Security).
2. Go to Google Account → Security → **App passwords**.
3. Create one called "Luphina" and copy the 16-character password.

## 2. Add the sending connection

**Connected apps → Email (SMTP)**

| Field | Value |
| --- | --- |
| Connection name | `mailbox` (the templates use this name) |
| host | `smtp.gmail.com` |
| port | `465` |
| username | your Gmail address |
| from_address | your Gmail address |
| password | the app password |

Optional: put your own address in **test_recipient** while you try things out. Every email then goes to you instead of the customer, with "[TEST for …]" in the subject.

## 3. Add the reading connection (only for email triggers)

**Connected apps → Incoming email (IMAP)**

| Field | Value |
| --- | --- |
| Connection name | e.g. `invoices-inbox` |
| host | `imap.gmail.com` |
| port | `993` |
| username | your Gmail address |
| password | the app password |

Luphina checks this mailbox every 30 seconds. Each new email starts one run, and it marks the email as read once its run has started.

> **Tip:** use a separate address or Gmail label for invoices, such as `invoices@yourshop.com`, so Luphina only reads the emails meant for it.

## Sending must be switched on

The person running your Luphina server controls a master switch for email sending (`EMAIL_SEND_ENABLED`). If approved emails show "sending disabled", ask them to switch it on.

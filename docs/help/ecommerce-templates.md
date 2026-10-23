# E-commerce templates

Every template emails customers **only after you approve** the message in **Approvals**.

## Order → invoice

**What it does:** when an order is paid, it creates a numbered invoice (INV-00001, INV-00002, …), remembers the order, and prepares an email with a link to the invoice.

**Set up:**

1. Add your business details in **Settings → Business details**.
2. Connect your Gmail as a sending connection named `mailbox` ([guide](connect-gmail.md)).
3. Install the template, then publish it.
4. Add the Shopify webhook for **Order payment** ([guide](connect-shopify.md)).

**Good to know:**

- Each order gets exactly one invoice, even if Shopify sends it twice.
- All invoices are listed under **Invoices**, and customers can print or save theirs as a PDF.

## Abandoned-cart follow-up

**What it does:** when a checkout starts, it waits an hour. If the checkout did not turn into an order, it prepares a friendly reminder with the customer's cart link.

**Set up:**

1. Install and publish **Order → invoice** first. It tells this workflow who bought.
2. Install and publish this template.
3. Add the Shopify webhook for **Checkout creation**.
4. Make sure the AutoFlow background worker is running (needed for the one-hour wait).

**Good to know:** if AutoFlow cannot be sure whether someone bought (for example because the order workflow isn't running yet), it **does not send** a reminder. Buyers are never nagged.

## Review reply assistant

**What it does:** when a review arrives, AI works out how the customer feels and drafts a warm, personal reply. It never promises refunds or discounts.

**Set up:**

1. Connect Gmail as `mailbox`.
2. Install and publish the template, then create its webhook URL.
3. In your review app, send new reviews to that URL with these fields: `rating`, `title`, `body`, `reviewer_name`, `reviewer_email`, `product_title`.

## Supplier invoice → spreadsheet

**What it does:** when a supplier emails an invoice (PDF, scan or plain text), AI reads the supplier, invoice number, dates, total and currency, and adds a row to your bookkeeping sheet.

**Set up:**

1. Connect the mailbox that receives supplier invoices as an **Incoming email** connection named `invoices-inbox` ([guide](connect-gmail.md)).
2. Connect Google with the name `sheets`.
3. In the last step, replace `PASTE-YOUR-SPREADSHEET-ID` with your sheet's id. It's the long code in the sheet's web address, between `/d/` and `/edit`.
4. Create a tab in the sheet called **Supplier invoices**.

**Good to know:**

- If the AI is unsure about a value, the run pauses in **Approvals** so you can check and correct it before the row is added.
- You can also upload invoices by hand. Change the trigger to "I upload a document" in **Edit**, then use **Run with a file…**.

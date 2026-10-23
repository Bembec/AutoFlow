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

## WooCommerce order → invoice

The same as Order → invoice, but for WooCommerce shops. It invoices orders once they are paid ("processing"), and an order that is updated later never gets a second invoice or email. See [Connect WooCommerce](connect-woocommerce.md).

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

## Shipping notification

When your store marks an order as shipped, the customer gets an email with the carrier and tracking link, after your approval. Orders shipped without a tracking number get no email.

**Needs:** a "fulfillment created" webhook from your store and the "mailbox" email connection.

## Refund → void invoice

When an order is refunded, its invoice is **voided**: the number is kept and the customer's link shows VOID. The customer then gets an email that the refund is on its way, after your approval. If the store sends the same refund twice, nothing happens the second time.

**Needs:** a "refund created" webhook (with the order id) and the **Order → invoice** workflow, which made the invoice.

## Weekly sales summary

Every Monday at 9:00 (UTC), AutoFlow fetches last week's orders from your shop's API and emails you a short summary: revenue, best sellers, anything unusual.

**Needs:** an API connection named "shop-api" and your own address in the last step.

## Low-stock alert (early access)

Every morning, AutoFlow checks your stock levels and emails you the products with fewer than 5 left. On days when everything is stocked, nothing is sent.

## Order lines → stock sheet (early access)

For every paid order, AutoFlow adds one row per product to a Google Sheet: order, product, quantity and price. Each line is written once, even if the store resends the order.

## Big-order thank-you (early access)

When an order over 150 is paid, the customer gets a personal thank-you from you, after your approval. Change the amount in the step's **Only run if…** condition.

## Support inbox assistant

When a customer emails your support address, AI sorts the message (return, delivery, complaint, product question) and drafts a friendly reply. You approve every reply before it is sent. The assistant never promises refunds, discounts or dates.

**Needs:** an incoming email connection named "support-inbox" and the "mailbox" email connection.

## WooCommerce "we're packing it" note

When a WooCommerce order starts processing, AutoFlow adds a note the customer can see, "Thanks, we're packing it now". WooCommerce emails it to them.

**Needs:** a WooCommerce order webhook and a WooCommerce connection named "store".

## Welcome first-time customers

When someone buys from you for the first time, they get a warm welcome email, after your approval. Returning customers get nothing extra.

## Ask for a review a week later

Seven days after an order is paid, the customer is asked how they like it and invited to leave a review, after your approval. Change the wait in the first step. Needs the background worker.

## Orders → spreadsheet, and WooCommerce orders → spreadsheet

Each paid order becomes one row in a Google Sheet: date or status, order number, customer, email and total.

## Customers → Airtable

Keeps a customer list in Airtable. Each order adds the customer, or updates them if they're already there (matched by email).

## Tag big orders (early access)

Shopify orders over 150 get the tag "big-order", so your team packs them first.

## Bad review alert (early access)

A review of 2 stars or less emails you straight away, so you can put it right quickly.

## Payment failed reminder

When a payment fails, the customer gets a friendly note with a link to pay again on your own shop, after your approval.

## WooCommerce completed: thank you

When a WooCommerce order is marked completed, the customer gets a thank-you and an invitation to review, after your approval.

## WooCommerce cancelled → void invoice (early access)

When a WooCommerce order is cancelled or refunded, its invoice is voided and keeps its number.

## Wholesale lead alert

AI spots wholesale or bulk enquiries in your inbox and emails you a short summary, so big buyers never wait.

> **Early access** templates use comparisons or loops. They appear in your workspace once **smarter logic** is switched on (see "Conditions and loops").


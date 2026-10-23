# Connect Shopify

There are two ways AutoFlow works with your store:

- **Webhooks:** Shopify *tells* AutoFlow when something happens (an order is paid, a checkout starts). The e-commerce templates need these.
- **Admin API access token:** AutoFlow *acts* in your store (adds tags or notes to orders). This is optional.

## Webhooks (for the templates)

1. In AutoFlow, open the workflow (e.g. **Order → invoice**), go to the **Trigger** tab and press **Create webhook URL**. Copy the URL. (You'll add Shopify's signing secret in step 4.)
2. In Shopify admin, open **Settings → Notifications → Webhooks** and click **Create webhook**:
   - **Event:** *Order payment* for Order → invoice, or *Checkout creation* for the abandoned-cart follow-up.
   - **Format:** JSON.
   - **URL:** paste the AutoFlow URL.
3. Shopify shows a line like *"Your webhooks will be signed with …"*. Copy that signing secret.
4. Back in AutoFlow's **Trigger** tab, choose **Who sends it? → Shopify**, paste the signing secret and press **Update webhook**. The URL stays the same.
5. Press **Send test notification** in Shopify. A run should appear in AutoFlow's **Run history**.

AutoFlow ignores anything that is not signed with your secret. If Shopify sends the same order twice, AutoFlow still creates only one invoice.

## Admin API token (optional, for tagging orders)

1. In Shopify admin, create a custom app for your store (**Settings → Apps and sales channels → Develop apps**) and give it the **read_orders** and **write_orders** Admin API scopes.
2. Install the app and copy its **Admin API access token** (it starts with `shpat_`).
3. In AutoFlow: **Connected apps → Shopify store**
   - **shop_domain:** `your-store.myshopify.com` (exactly this form)
   - **access_token:** the token

You can then add steps such as **shopify tag order** (e.g. tag "invoiced") or **shopify set order note** to your workflows.

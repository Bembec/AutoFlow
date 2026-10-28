# Connect WooCommerce

## Order webhook (for "WooCommerce order → invoice")

1. In Luphina, install and publish the **WooCommerce order → invoice** template.
2. On its **Trigger** tab, choose **Who sends it? → WooCommerce**. Make up a long secret of at least 16 characters, enter it, and press **Create webhook URL**. Copy the URL.
3. In WordPress, open **WooCommerce → Settings → Advanced → Webhooks → Add webhook**:
   - **Status:** Active
   - **Topic:** *Order updated* (fires when an order is paid and on later changes)
   - **Delivery URL:** the Luphina URL
   - **Secret:** the same secret as in step 2
   - **API version:** the newest offered
4. Save. WooCommerce sends a quick "ping" that Luphina answers automatically.

Luphina only creates an invoice once an order is paid (status "processing" or later). Each order gets exactly one invoice and one email, however many times WooCommerce reports an update.

## REST API keys (optional, for notes and statuses)

1. In WordPress, open **WooCommerce → Settings → Advanced → REST API → Add key**. Choose *Read/Write* permissions and copy the **consumer key** and **consumer secret**.
2. In Luphina: **Connected apps → WooCommerce store**
   - **store_url:** your shop address, starting with `https://`
   - **consumer_key** and **consumer_secret:** from step 1

Workflows can then:

- **Add a note** to an order, either private or visible to the customer.
- **Change an order's status.** This always waits for your approval, because WooCommerce may email the customer about it.

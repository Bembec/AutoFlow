# Conditions and loops

> These options appear when **smarter logic** is switched on for your workspace. During the early rollout, ask support to switch it on.

## Only run a step if…

Open a step in the editor and expand **Only run if…**. Pick a value, a comparison and what to compare it with:

| Comparison | Example |
| --- | --- |
| is / is not | the payment method **is** "invoice" |
| contains / doesn't contain | the order tags **don't contain** "wholesale" |
| has a value / is empty | the gift message **has a value** |
| is more than / is at least | the order total **is more than** 200 |
| is less than / is at most | the stock count **is at most** 5 |

Number comparisons understand values like `47.60` or `1,200.50`. If a value isn't a number, the comparison is simply false, so the step is skipped and nothing breaks.

Add more conditions with **+ Add another condition**, then choose:
- **all of these are true** (AND), for example: total over 200 **and** shipping to a new customer;
- **any of these is true** (OR), for example: tagged "vip" **or** tagged "gift".

## Repeat a step for each item

Expand **Repeat for each item…** and choose a list, such as the order's line items. The step then runs once per item. In its inputs you can insert:
- **Current item** and its fields, such as `{{item.title}}` or `{{item.quantity}}`;
- **Item number**, `{{index}}`, counting from 0.

Example: *for each line item, add a row to the stock sheet with the product name and quantity.*

Good to know:
- **Up to 100 items** per run. A longer list fails with a clear message instead of running half-way.
- **Nothing runs twice.** AutoFlow remembers which items are done. If item 3 fails, fixing the cause and retrying continues from item 3. If AutoFlow isn't sure whether an item went through, you choose: retry it, or confirm it happened and carry on.
- Later steps can use the results: `steps.<step>.output.count` is the number of items, and `steps.<step>.output.items` holds each item's result.
- **Billing:** each item that calls an app counts as one task. Test runs are still free.
- **Not every step can loop.** Emails and AI steps have their own limits and approvals, so they can't be repeated in a loop. Send one summary email after the loop instead.

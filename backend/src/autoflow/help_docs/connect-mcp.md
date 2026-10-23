# Use tools from MCP servers

MCP (Model Context Protocol) is the standard way AI services offer their tools to other apps. A product catalogue service, for example, might offer "search products". AutoFlow can use those tools as workflow steps.

## Connect a server

1. Go to **Connected apps → Connect an app → MCP server**.
2. Fill in:
   - **server url:** the server's MCP address. It must start with `https://`.
   - **allowed tools:** the tools workflows may use, separated by commas, for example `search_products, create_discount`. Use `*` only for servers you fully trust.
   - **token:** if the server needs one. It's encrypted and never shown again.
3. Press **Show tools** on the connection to see every tool the server offers. Each tool is marked **read-only** or **can change things**, and tools you haven't allowed are greyed out.
4. **Check connection** confirms that AutoFlow can reach the server and that your allowed tools exist.

## Use a tool in a workflow

There are two steps:

- **Read from an MCP tool** (`mcp_read`) is for looking things up: search, fetch, get. It only runs tools the server marks as read-only. Because reading changes nothing, it also runs during test runs.
- **Use an MCP tool** (`mcp_call_tool`) is for tools that change something, such as creating a discount code. It **always waits for your approval**, and test runs only pretend.

In both, set:
- **tool:** the tool's name;
- **arguments:** its inputs as an object, for example `{"query": "{{trigger.text}}"}`.

The answer is available to later steps as `text` and, if the tool gives one, structured `data`.

## Safety

- Only the tools you allowed can be used, and only over https to public addresses.
- What a tool returns is treated as untrusted data. AI steps that read it keep their prompt-injection checks, and nothing gets new permissions because of text inside a result.
- Results are limited in size, and failures are explained in plain words.

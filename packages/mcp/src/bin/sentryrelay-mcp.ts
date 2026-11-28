#!/usr/bin/env node
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createSentryRelayMcpServer, MCP_SERVER_NAME, MCP_SERVER_VERSION } from '../index.js';

async function main(): Promise<void> {
  const apiKey = process.env.SENTRY_RELAY_API_KEY;
  if (!apiKey) {
    process.stderr.write(
      `[${MCP_SERVER_NAME} v${MCP_SERVER_VERSION}] Error: SENTRY_RELAY_API_KEY environment variable is required.\n` +
        `Set SENTRY_RELAY_API_KEY="sr_live_..." or "sr_test_..." in your agent configuration.\n`,
    );
    process.exit(1);
  }

  const baseUrl = process.env.SENTRY_RELAY_BASE_URL;
  const server = createSentryRelayMcpServer({ apiKey, baseUrl });
  const transport = new StdioServerTransport();

  await server.connect(transport);
}

main().catch((err) => {
  process.stderr.write(
    `[${MCP_SERVER_NAME}] Fatal: ${err instanceof Error ? err.stack : String(err)}\n`,
  );
  process.exit(1);
});

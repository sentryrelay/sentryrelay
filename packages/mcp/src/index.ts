import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { PRODUCT_NAME, SentryRelay, SentryRelayApiError } from '@sentryrelay/sdk';

export const MCP_SERVER_NAME = 'sentry-relay-mcp';
export const MCP_SERVER_VERSION = '0.2.0';

export const SENTRY_RELAY_MCP_TOOLS = [
  'wait_for_verification_code',
  'get_latest_verification_code',
  'get_totp_code',
  'list_identities',
  'create_identity',
  'store_totp_secret',
] as const;

export type SentryRelayMcpToolName = (typeof SENTRY_RELAY_MCP_TOOLS)[number];

export interface McpToolMetadata {
  name: SentryRelayMcpToolName;
  description: string;
  inputSchema: {
    type: 'object';
    properties: Record<string, unknown>;
    required?: string[];
  };
}

export const MCP_TOOL_DEFINITIONS: readonly McpToolMetadata[] = [
  {
    name: 'wait_for_verification_code',
    description:
      'Long-polls an Identity inbox until a fresh OTP code or magic link arrives and returns structured JSON ready for browser input.',
    inputSchema: {
      type: 'object',
      properties: {
        identity: {
          type: 'string',
          description: 'Identity ID or unique slug to monitor.',
        },
        channel: {
          type: 'string',
          enum: ['email', 'sms'],
          description: 'Optional channel filter (email or sms).',
        },
        sender: {
          type: 'string',
          description:
            'Optional sender substring filter (e.g. "stripe.com", "github.com", "+12065550100").',
        },
        subject: {
          type: 'string',
          description: 'Optional email subject substring filter.',
        },
        timeoutSeconds: {
          type: 'integer',
          minimum: 1,
          maximum: 45,
          default: 30,
          description: 'Long-polling timeout in seconds (1..45, default: 30).',
        },
        sinceMs: {
          type: 'integer',
          description:
            'Epoch millisecond timestamp to search from (defaults to 15 seconds in the past).',
        },
        includeNonAuth: {
          type: 'boolean',
          default: false,
          description:
            'Include non-auth emails/SMS (e.g. custom onboarding emails or vendor confirmation links) in addition to extracted OTPs and magic links (default: false).',
        },
      },
      required: ['identity'],
    },
  },
  {
    name: 'get_latest_verification_code',
    description:
      'Performs a non-blocking lookback check on an Identity timeline for a recently delivered OTP, magic link, or verification message.',
    inputSchema: {
      type: 'object',
      properties: {
        identity: {
          type: 'string',
          description: 'Identity ID or unique slug.',
        },
        channel: {
          type: 'string',
          enum: ['email', 'sms'],
          description: 'Optional channel filter (email or sms).',
        },
        sender: {
          type: 'string',
          description: 'Optional sender substring filter.',
        },
        lookbackSeconds: {
          type: 'integer',
          minimum: 1,
          maximum: 300,
          default: 60,
          description: 'Seconds into the past to check for delivered codes (default: 60).',
        },
        consume: {
          type: 'boolean',
          default: true,
          description: 'Whether to atomically consume the code (default: true).',
        },
        includeNonAuth: {
          type: 'boolean',
          default: false,
          description:
            'Include non-auth emails/SMS (e.g. custom onboarding emails or vendor confirmation links) in addition to extracted OTPs and magic links (default: false).',
        },
      },
      required: ['identity'],
    },
  },
  {
    name: 'get_totp_code',
    description:
      'Generates a live RFC 6238 Authenticator (TOTP) code for a vaulted service secret, automatically waiting if the window is expiring (<4s).',
    inputSchema: {
      type: 'object',
      properties: {
        identity: {
          type: 'string',
          description: 'Identity ID or unique slug.',
        },
        secretId: {
          type: 'string',
          description: 'ID of the vaulted TOTP service secret (e.g. "github_ops", "aws_root").',
        },
        autoWaitFreshWindow: {
          type: 'boolean',
          default: true,
          description:
            'Transparently wait if remaining code window is <4s to guarantee a fresh 26-30s code (default: true).',
        },
      },
      required: ['identity', 'secretId'],
    },
  },
  {
    name: 'list_identities',
    description:
      'Lists accessible Identities along with their assigned email address, SMS number, and TOTP secret IDs.',
    inputSchema: {
      type: 'object',
      properties: {
        search: {
          type: 'string',
          description: 'Optional substring to filter identities by name, email handle, or ID.',
        },
        limit: {
          type: 'integer',
          minimum: 1,
          maximum: 100,
          description: 'Maximum number of identities to return (default: 50).',
        },
      },
    },
  },
  {
    name: 'create_identity',
    description: 'Creates a new isolated Identity inbox for an autonomous workflow.',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Human-readable label for the Identity inbox.',
        },
        emailHandle: {
          type: 'string',
          description: 'Optional custom email prefix before @sentryrelay.com.',
        },
        fallbackEmail: {
          type: 'string',
          description: 'Optional human fallback destination email address for non-auth messages.',
        },
      },
      required: ['name'],
    },
  },
  {
    name: 'store_totp_secret',
    description: 'Vaults an otpauth:// URI or Base32 TOTP secret under an Identity.',
    inputSchema: {
      type: 'object',
      properties: {
        identity: {
          type: 'string',
          description: 'Identity ID or unique slug.',
        },
        secretId: {
          type: 'string',
          description: 'Unique identifier for this TOTP secret (e.g. "github_ops").',
        },
        otpauthUriOrSecret: {
          type: 'string',
          description: 'otpauth:// URI or raw Base32 secret string.',
        },
        issuer: {
          type: 'string',
          description: 'Optional service issuer label (e.g. "GitHub", "AWS", "Stripe").',
        },
      },
      required: ['identity', 'secretId', 'otpauthUriOrSecret'],
    },
  },
] as const;

export const MCP_TOOL_CATALOG = MCP_TOOL_DEFINITIONS;

export interface McpToolResult {
  content: Array<{
    type: 'text';
    text: string;
  }>;
  isError?: boolean;
}

/**
 * Executes a canonical Sentry Relay MCP tool using the SentryRelay client.
 */
export async function executeMcpTool(
  client: SentryRelay,
  toolName: string,
  args: Record<string, unknown> = {},
): Promise<McpToolResult> {
  try {
    switch (toolName) {
      case 'wait_for_verification_code': {
        const identity = String(args.identity ?? '');
        if (!identity) {
          throw new SentryRelayApiError(
            'VALIDATION_ERROR',
            'Missing required parameter "identity".',
          );
        }
        const timeoutSeconds =
          typeof args.timeoutSeconds === 'number' ? args.timeoutSeconds : undefined;
        const sinceMs = typeof args.sinceMs === 'number' ? args.sinceMs : undefined;
        const channel =
          args.channel === 'email' || args.channel === 'sms' ? args.channel : undefined;
        const sender = typeof args.sender === 'string' ? args.sender : undefined;
        const subject = typeof args.subject === 'string' ? args.subject : undefined;
        const includeNonAuth =
          typeof args.includeNonAuth === 'boolean' ? args.includeNonAuth : undefined;

        const result = await client.identities.wait(identity, {
          channel,
          sender,
          subject,
          timeout: timeoutSeconds,
          since: sinceMs,
          includeNonAuth,
        });

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'get_latest_verification_code': {
        const identity = String(args.identity ?? '');
        if (!identity) {
          throw new SentryRelayApiError(
            'VALIDATION_ERROR',
            'Missing required parameter "identity".',
          );
        }
        const lookbackSeconds =
          typeof args.lookbackSeconds === 'number' ? args.lookbackSeconds : undefined;
        const channel =
          args.channel === 'email' || args.channel === 'sms' ? args.channel : undefined;
        const sender = typeof args.sender === 'string' ? args.sender : undefined;
        const consume = typeof args.consume === 'boolean' ? args.consume : undefined;
        const includeNonAuth =
          typeof args.includeNonAuth === 'boolean' ? args.includeNonAuth : undefined;

        const result = await client.identities.latest(identity, {
          channel,
          sender,
          lookbackSeconds,
          consume,
          includeNonAuth,
        });

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'get_totp_code': {
        const identity = String(args.identity ?? '');
        const secretId = String(args.secretId ?? '');
        if (!identity || !secretId) {
          throw new SentryRelayApiError(
            'VALIDATION_ERROR',
            'Missing required parameters "identity" or "secretId".',
          );
        }
        const autoWaitFreshWindow =
          typeof args.autoWaitFreshWindow === 'boolean' ? args.autoWaitFreshWindow : true;

        const result = await client.totp.get(identity, secretId, {
          autoWaitFreshWindow,
        });

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'list_identities': {
        const search = typeof args.search === 'string' ? args.search.toLowerCase().trim() : '';
        const limit = typeof args.limit === 'number' ? args.limit : undefined;

        const result = await client.identities.list({ limit });
        let items = result.items;

        if (search) {
          items = items.filter(
            (id) =>
              id.name.toLowerCase().includes(search) ||
              id.emailHandle.toLowerCase().includes(search) ||
              id.id.toLowerCase().includes(search),
          );
        }

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({ items, count: items.length }, null, 2),
            },
          ],
        };
      }

      case 'create_identity': {
        const name = String(args.name ?? '').trim();
        if (!name) {
          throw new SentryRelayApiError('VALIDATION_ERROR', 'Missing required parameter "name".');
        }
        const emailHandle =
          typeof args.emailHandle === 'string' && args.emailHandle.trim()
            ? args.emailHandle.trim()
            : undefined;
        const fallbackEmail =
          typeof args.fallbackEmail === 'string' && args.fallbackEmail.trim()
            ? args.fallbackEmail.trim()
            : undefined;

        const created = await client.identities.create({
          name,
          emailHandle,
          fallback: fallbackEmail
            ? {
                enabled: true,
                fallbackEmail,
              }
            : undefined,
        });

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({ identity: created }, null, 2),
            },
          ],
        };
      }

      case 'store_totp_secret': {
        const identity = String(args.identity ?? '');
        const secretId = String(args.secretId ?? '');
        const rawUriOrSecret = String(args.otpauthUriOrSecret ?? '').trim();
        const issuer = typeof args.issuer === 'string' ? args.issuer.trim() : undefined;

        if (!identity || !secretId || !rawUriOrSecret) {
          throw new SentryRelayApiError(
            'VALIDATION_ERROR',
            'Missing required parameters "identity", "secretId", or "otpauthUriOrSecret".',
          );
        }

        let stored;
        if (rawUriOrSecret.startsWith('otpauth://')) {
          stored = await client.totp.create(identity, {
            id: secretId,
            otpauthUri: rawUriOrSecret,
          });
        } else {
          stored = await client.totp.create(identity, {
            id: secretId,
            secret: rawUriOrSecret,
            issuer: issuer ?? 'Custom',
            accountLabel: secretId,
          });
        }

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({ secret: stored }, null, 2),
            },
          ],
        };
      }

      default:
        throw new SentryRelayApiError('NOT_FOUND', `Unknown MCP tool "${toolName}".`);
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const code = err instanceof SentryRelayApiError ? err.code : 'INTERNAL_ERROR';
    return {
      content: [
        {
          type: 'text',
          text: `Error [${code}]: ${message}`,
        },
      ],
      isError: true,
    };
  }
}

/**
 * Creates and configures a standard Model Context Protocol Server.
 */
export function createSentryRelayMcpServer(options: {
  apiKey?: string;
  baseUrl?: string;
  client?: SentryRelay;
}): Server {
  const client =
    options.client ??
    new SentryRelay({
      apiKey: options.apiKey ?? process.env.SENTRY_RELAY_API_KEY ?? '',
      baseUrl: options.baseUrl ?? process.env.SENTRY_RELAY_BASE_URL,
    });

  const server = new Server(
    {
      name: MCP_SERVER_NAME,
      version: MCP_SERVER_VERSION,
    },
    {
      capabilities: {
        tools: {},
      },
    },
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: MCP_TOOL_DEFINITIONS.map((def) => ({
        name: def.name,
        description: def.description,
        inputSchema: def.inputSchema,
      })),
    };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: toolArgs } = request.params;
    const result = await executeMcpTool(client, name, (toolArgs as Record<string, unknown>) ?? {});
    return {
      content: result.content,
      isError: result.isError,
    };
  });

  return server;
}

export interface JsonRpcRequest {
  jsonrpc: '2.0';
  id?: string | number | null;
  method: string;
  params?: Record<string, unknown>;
}

export interface JsonRpcResponse {
  jsonrpc: '2.0';
  id: string | number | null;
  result?: unknown;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

/**
 * Dispatches a standard MCP JSON-RPC message (used by HTTP Streamable MCP route).
 */
export async function dispatchMcpJsonRpc(
  payload: unknown,
  client: SentryRelay,
): Promise<JsonRpcResponse | JsonRpcResponse[] | null> {
  if (Array.isArray(payload)) {
    const responses: JsonRpcResponse[] = [];
    for (const req of payload) {
      const res = await dispatchSingleMcpJsonRpc(req, client);
      if (res) responses.push(res);
    }
    return responses;
  }
  return dispatchSingleMcpJsonRpc(payload, client);
}

async function dispatchSingleMcpJsonRpc(
  req: unknown,
  client: SentryRelay,
): Promise<JsonRpcResponse | null> {
  if (!req || typeof req !== 'object') {
    return {
      jsonrpc: '2.0',
      id: null,
      error: { code: -32700, message: 'Parse error' },
    };
  }

  const { jsonrpc, id = null, method, params = {} } = req as JsonRpcRequest;
  if (jsonrpc !== '2.0' || typeof method !== 'string') {
    return {
      jsonrpc: '2.0',
      id,
      error: { code: -32600, message: 'Invalid Request' },
    };
  }

  // Notifications (requests without an id) do not produce responses
  const isNotification = id === undefined || id === null;

  switch (method) {
    case 'initialize': {
      return {
        jsonrpc: '2.0',
        id,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: {
            tools: {},
          },
          serverInfo: {
            name: MCP_SERVER_NAME,
            version: MCP_SERVER_VERSION,
          },
          instructions: `${PRODUCT_NAME} 2FA, OTP & Authenticator Vault MCP Server.`,
        },
      };
    }

    case 'notifications/initialized': {
      return null;
    }

    case 'ping': {
      return {
        jsonrpc: '2.0',
        id,
        result: {},
      };
    }

    case 'tools/list': {
      return {
        jsonrpc: '2.0',
        id,
        result: {
          tools: MCP_TOOL_DEFINITIONS.map((def) => ({
            name: def.name,
            description: def.description,
            inputSchema: def.inputSchema,
          })),
        },
      };
    }

    case 'tools/call': {
      const toolName = String((params as Record<string, unknown>).name ?? '');
      const toolArgs =
        ((params as Record<string, unknown>).arguments as Record<string, unknown>) ?? {};
      const result = await executeMcpTool(client, toolName, toolArgs);
      return {
        jsonrpc: '2.0',
        id,
        result,
      };
    }

    default: {
      if (isNotification) return null;
      return {
        jsonrpc: '2.0',
        id,
        error: { code: -32601, message: `Method not found: "${method}"` },
      };
    }
  }
}

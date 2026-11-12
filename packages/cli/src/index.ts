import { Command } from 'commander';
import { CLI_BINARY_NAME, PRODUCT_NAME, SentryRelayApiError } from '@sentryrelay/sdk';
import {
  clearCredentials,
  getCredentialsFilePath,
  loadCredentials,
  maskApiKey,
  resolveClient,
  saveCredentials,
} from './config.js';

export const CLI_VERSION = '0.2.0';

export function getCliBanner(): string {
  return `${PRODUCT_NAME} CLI (${CLI_BINARY_NAME}) v${CLI_VERSION}`;
}

export interface CliStreams {
  stdout?: { write: (str: string) => boolean | void };
  stderr?: { write: (str: string) => boolean | void };
  fetch?: typeof fetch;
}

export function buildCliProgram(streams?: CliStreams): Command {
  const stdout = streams?.stdout ?? process.stdout;
  const stderr = streams?.stderr ?? process.stderr;

  const program = new Command();

  program
    .name(CLI_BINARY_NAME)
    .description(`${PRODUCT_NAME} CLI — The 2FA, OTP & Authenticator Vault for Autonomous Software`)
    .version(CLI_VERSION, '-v, --version', 'Output the current version')
    .option('-k, --key <token>', 'Sentry Relay API key (sr_live_... or sr_test_...)')
    .option('-u, --url <baseUrl>', 'Sentry Relay API base URL');

  // srelay login
  program
    .command('login')
    .description(
      'Authenticate and securely store Sentry Relay credentials in ~/.config/sentryrelay/credentials.json (mode 0600)',
    )
    .option('-k, --key <token>', 'API key to store')
    .option('-u, --url <baseUrl>', 'Custom base URL')
    .action(async (cmdOptions) => {
      try {
        const apiKey = cmdOptions.key ?? program.opts().key;
        if (!apiKey) {
          stderr.write('Error: --key is required. Example: srelay login --key sr_live_...\n');
          process.exitCode = 1;
          return;
        }

        const baseUrl = cmdOptions.url ?? program.opts().url;
        const savedPath = saveCredentials({ apiKey, baseUrl });
        stdout.write(
          `✓ Successfully authenticated. Saved credentials to ${savedPath} (mode 0600).\n`,
        );
      } catch (err) {
        stderr.write(`Error: ${err instanceof Error ? err.message : String(err)}\n`);
        process.exitCode = 1;
      }
    });

  // srelay logout
  program
    .command('logout')
    .description('Remove locally saved credentials')
    .action(() => {
      const removed = clearCredentials();
      if (removed) {
        stdout.write('✓ Logged out. Saved credentials have been removed.\n');
      } else {
        stdout.write('No active credentials file found.\n');
      }
    });

  // srelay whoami
  program
    .command('whoami')
    .description('Show currently authenticated API key and endpoint configuration')
    .action(async () => {
      try {
        const globalOpts = program.opts();
        const client = resolveClient({
          key: globalOpts.key,
          url: globalOpts.url,
          fetch: streams?.fetch,
        });

        const saved = loadCredentials();
        const activeKey = globalOpts.key ?? process.env.SENTRY_RELAY_API_KEY ?? saved?.apiKey ?? '';

        stdout.write(`Sentry Relay Configuration:\n`);
        stdout.write(`  Key:      ${maskApiKey(activeKey)}\n`);
        stdout.write(`  Base URL: ${client.baseUrl}\n`);
        stdout.write(`  Config:   ${getCredentialsFilePath()}\n`);
      } catch (err) {
        stderr.write(`Error: ${err instanceof Error ? err.message : String(err)}\n`);
        process.exitCode = 1;
      }
    });

  // srelay identities
  const identitiesCmd = program.command('identities').description('Manage Sentry Relay Identities');

  identitiesCmd
    .command('list')
    .description('List accessible Identities')
    .option('-l, --limit <number>', 'Maximum number of items to return', '50')
    .option('--json', 'Output result in JSON format')
    .action(async (cmdOptions) => {
      try {
        const globalOpts = program.opts();
        const client = resolveClient({
          key: globalOpts.key,
          url: globalOpts.url,
          fetch: streams?.fetch,
        });

        const limit = Number.parseInt(cmdOptions.limit, 10);
        const res = await client.identities.list({
          limit: Number.isFinite(limit) ? limit : 50,
        });

        if (cmdOptions.json) {
          stdout.write(`${JSON.stringify(res, null, 2)}\n`);
          return;
        }

        if (res.items.length === 0) {
          stdout.write('No identities found.\n');
          return;
        }

        stdout.write(`Found ${res.items.length} identity(ies):\n`);
        for (const id of res.items) {
          const smsStr = id.smsPhoneNumber ? ` | SMS: ${id.smsPhoneNumber}` : '';
          stdout.write(`- [${id.id}] ${id.name} (${id.emailAddress}${smsStr})\n`);
        }
      } catch (err) {
        stderr.write(`Error: ${err instanceof Error ? err.message : String(err)}\n`);
        process.exitCode = 1;
      }
    });

  identitiesCmd
    .command('create <name>')
    .description('Create a new dedicated Identity')
    .option('--email-handle <handle>', 'Custom email handle prefix')
    .option('--fallback-email <email>', 'Human fallback destination email address')
    .option('--json', 'Output result in JSON format')
    .action(async (name, cmdOptions) => {
      try {
        const globalOpts = program.opts();
        const client = resolveClient({
          key: globalOpts.key,
          url: globalOpts.url,
          fetch: streams?.fetch,
        });

        const created = await client.identities.create({
          name,
          emailHandle: cmdOptions.emailHandle,
          fallback: cmdOptions.fallbackEmail
            ? {
                enabled: true,
                fallbackEmail: cmdOptions.fallbackEmail,
              }
            : undefined,
        });

        if (cmdOptions.json) {
          stdout.write(`${JSON.stringify(created, null, 2)}\n`);
          return;
        }

        stdout.write(`✓ Identity created successfully:\n`);
        stdout.write(`  ID:    ${created.id}\n`);
        stdout.write(`  Name:  ${created.name}\n`);
        stdout.write(`  Email: ${created.emailAddress}\n`);
      } catch (err) {
        stderr.write(`Error: ${err instanceof Error ? err.message : String(err)}\n`);
        process.exitCode = 1;
      }
    });

  identitiesCmd
    .command('inspect <idOrSlug>')
    .description('Inspect details and configuration of an Identity')
    .option('--json', 'Output result in JSON format')
    .action(async (idOrSlug, cmdOptions) => {
      try {
        const globalOpts = program.opts();
        const client = resolveClient({
          key: globalOpts.key,
          url: globalOpts.url,
          fetch: streams?.fetch,
        });

        const identity = await client.identities.get(idOrSlug);

        if (cmdOptions.json) {
          stdout.write(`${JSON.stringify(identity, null, 2)}\n`);
          return;
        }

        stdout.write(`Identity: ${identity.name} [${identity.id}]\n`);
        stdout.write(`  Status:    ${identity.status}\n`);
        stdout.write(`  Email:     ${identity.emailAddress}\n`);
        stdout.write(`  Phone:     ${identity.smsPhoneNumber ?? 'None (Simulated SMS)'}\n`);
        stdout.write(`  TOTP Keys: ${identity.totpSecretCount}\n`);
      } catch (err) {
        stderr.write(`Error: ${err instanceof Error ? err.message : String(err)}\n`);
        process.exitCode = 1;
      }
    });

  // srelay wait
  program
    .command('wait <identity>')
    .description('Hold connection open until fresh OTP or magic link arrives')
    .option('-s, --sender <string>', 'Filter by sender substring (e.g. stripe.com)')
    .option('-c, --channel <channel>', 'Filter by channel (email or sms)')
    .option('--subject <string>', 'Filter by email subject')
    .option('-t, --timeout <seconds>', 'Timeout in seconds (1..45)', '30')
    .option('--since <ms>', 'Epoch millisecond search window start')
    .option('--no-consume', 'Do not atomically mark event consumed')
    .option(
      '--include-non-auth',
      'Include non-auth emails/SMS (with sanitized textBody and extracted links) in addition to OTPs and magic links',
    )
    .option(
      '--raw',
      'Output ONLY the extracted OTP code or magic link for scripts (e.g. CODE=$(srelay wait bot --raw))',
    )
    .option('--json', 'Output full response in JSON format')
    .action(async (identity, cmdOptions) => {
      try {
        const globalOpts = program.opts();
        const client = resolveClient({
          key: globalOpts.key,
          url: globalOpts.url,
          fetch: streams?.fetch,
        });

        const timeout = Number.parseInt(cmdOptions.timeout, 10);
        const since = cmdOptions.since ? Number.parseInt(cmdOptions.since, 10) : undefined;
        const channel =
          cmdOptions.channel === 'email' || cmdOptions.channel === 'sms'
            ? cmdOptions.channel
            : undefined;

        const result = await client.identities.wait(identity, {
          sender: cmdOptions.sender,
          channel,
          subject: cmdOptions.subject,
          timeout: Number.isFinite(timeout) ? timeout : 30,
          since: Number.isFinite(since) ? since : undefined,
          consume: cmdOptions.consume,
          includeNonAuth: cmdOptions.includeNonAuth === true ? true : undefined,
        });

        if (cmdOptions.raw) {
          if (result.matched && result.event?.otpCode) {
            stdout.write(`${result.event.otpCode}\n`);
            return;
          }
          if (result.matched && result.event?.magicLink) {
            stdout.write(`${result.event.magicLink}\n`);
            return;
          }
          if (result.matched && result.event?.links && result.event.links.length > 0) {
            stdout.write(`${result.event.links[0]!.href}\n`);
            return;
          }
          process.exitCode = 1;
          return;
        }

        if (cmdOptions.json) {
          stdout.write(`${JSON.stringify(result, null, 2)}\n`);
          return;
        }

        if (result.matched && result.event) {
          stdout.write(`✓ Received verification message in ${result.waitDurationMs}ms:\n`);
          stdout.write(`  Code:    ${result.event.otpCode ?? 'None (Link/Message only)'}\n`);
          if (result.event.magicLink) {
            stdout.write(`  Link:    ${result.event.magicLink}\n`);
          }
          stdout.write(`  Channel: ${result.event.channel}\n`);
          stdout.write(`  Sender:  ${result.event.sender}\n`);
          if (result.event.subject) {
            stdout.write(`  Subject: ${result.event.subject}\n`);
          }
          if (result.event.links && result.event.links.length > 0) {
            stdout.write(`  Links:   ${result.event.links.map((l) => l.href).join(', ')}\n`);
          }
        } else {
          stdout.write(`Timed out waiting for verification code (${timeout}s).\n`);
          process.exitCode = 1;
        }
      } catch (err) {
        if (!cmdOptions.raw) {
          stderr.write(`Error: ${err instanceof Error ? err.message : String(err)}\n`);
        }
        process.exitCode = 1;
      }
    });

  // srelay totp
  const totpCmd = program
    .command('totp')
    .description('Manage and generate RFC 6238 Authenticator (TOTP) codes');

  totpCmd
    .command('add <identity> <secretId>')
    .description('Vault a TOTP secret from an otpauth:// URI or Base32 secret')
    .option('--uri <otpauthUri>', 'Full otpauth://totp/... URI')
    .option('--secret <base32Secret>', 'Raw Base32 secret seed')
    .option('--issuer <issuer>', 'Service issuer label (e.g. GitHub, AWS)')
    .option('--json', 'Output result in JSON format')
    .action(async (identity, secretId, cmdOptions) => {
      try {
        const globalOpts = program.opts();
        const client = resolveClient({
          key: globalOpts.key,
          url: globalOpts.url,
          fetch: streams?.fetch,
        });

        if (!cmdOptions.uri && !cmdOptions.secret) {
          stderr.write('Error: Either --uri or --secret must be provided.\n');
          process.exitCode = 1;
          return;
        }

        let created;
        if (cmdOptions.uri) {
          created = await client.totp.create(identity, {
            id: secretId,
            otpauthUri: cmdOptions.uri,
          });
        } else {
          created = await client.totp.create(identity, {
            id: secretId,
            secret: cmdOptions.secret,
            issuer: cmdOptions.issuer ?? 'Custom',
            accountLabel: secretId,
          });
        }

        if (cmdOptions.json) {
          stdout.write(`${JSON.stringify(created, null, 2)}\n`);
          return;
        }

        stdout.write(`✓ Vaulted TOTP secret "${secretId}" under identity "${identity}".\n`);
      } catch (err) {
        stderr.write(`Error: ${err instanceof Error ? err.message : String(err)}\n`);
        process.exitCode = 1;
      }
    });

  totpCmd
    .command('get <identity> <secretId>')
    .description('Generate live RFC 6238 code for vaulted service secret')
    .option(
      '--raw',
      'Output ONLY the 6- or 8-digit code for scripts (e.g. CODE=$(srelay totp get bot github --raw))',
    )
    .option('--no-auto-wait', 'Do not auto-wait for rollover if remaining window is <4s')
    .option('--json', 'Output full result in JSON format')
    .action(async (identity, secretId, cmdOptions) => {
      try {
        const globalOpts = program.opts();
        const client = resolveClient({
          key: globalOpts.key,
          url: globalOpts.url,
          fetch: streams?.fetch,
        });

        const res = await client.totp.get(identity, secretId, {
          autoWaitFreshWindow: cmdOptions.autoWait !== false,
        });

        if (cmdOptions.raw) {
          stdout.write(`${res.code}\n`);
          return;
        }

        if (cmdOptions.json) {
          stdout.write(`${JSON.stringify(res, null, 2)}\n`);
          return;
        }

        stdout.write(`TOTP Code: ${res.code} (valid for ${res.remainingSeconds}s)\n`);
      } catch (err) {
        if (!cmdOptions.raw) {
          stderr.write(`Error: ${err instanceof Error ? err.message : String(err)}\n`);
        }
        process.exitCode = 1;
      }
    });

  return program;
}

export * from './config.js';

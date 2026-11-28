#!/usr/bin/env node
import { buildCliProgram } from './index.js';

const program = buildCliProgram();
program.parseAsync(process.argv).catch((err) => {
  process.stderr.write(`Fatal: ${err instanceof Error ? err.message : String(err)}\n`);
  process.exit(1);
});

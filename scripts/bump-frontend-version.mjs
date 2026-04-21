/**
 * Increments APP_VERSION in frontend/lib/version.ts (patch segment: 1.43 -> 1.44).
 * Run from repo root: node scripts/bump-frontend-version.mjs
 */
import fs from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const file = join(root, "frontend/lib/version.ts");

let content = fs.readFileSync(file, "utf8");
const m = content.match(/export const APP_VERSION = "(\d+)\.(\d+)"/);
if (!m) {
  console.error("Could not parse APP_VERSION in frontend/lib/version.ts");
  process.exit(1);
}
const major = m[1];
const patch = parseInt(m[2], 10) + 1;
const next = `${major}.${patch}`;
content = content.replace(
  /export const APP_VERSION = "[^"]+"/,
  `export const APP_VERSION = "${next}"`
);
fs.writeFileSync(file, content);
console.log(`APP_VERSION ${m[1]}.${m[2]} -> ${next}`);

import { cpSync, existsSync, rmSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(web, "out");
const dest = join(web, "..", "src", "mldoctor", "static_next");
if (!existsSync(join(src, "index.html"))) { console.error("web/out missing - run next build first"); process.exit(1); }
rmSync(dest, { recursive: true, force: true });
cpSync(src, dest, { recursive: true });
console.log(`copied ${src} -> ${dest}`);

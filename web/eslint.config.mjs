import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
// typescript-eslint does not yet support TypeScript 7; typing is enforced by `tsc --noEmit`.
export default defineConfig([...nextVitals, globalIgnores([".next/**", "out/**", "scripts/**"])]);

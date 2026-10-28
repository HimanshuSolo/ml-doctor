import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "MLDoctor — Mission Control", description: "Reproduce, investigate, patch, verify.",
  icons: { icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><rect width='16' height='16' fill='%230b1526'/><text x='2' y='12' font-size='10' fill='%232dd4bf'>M</text></svg>" } };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}

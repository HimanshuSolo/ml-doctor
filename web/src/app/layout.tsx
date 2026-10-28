import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "MLDoctor — Mission Control", description: "Reproduce, investigate, patch, verify." };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}

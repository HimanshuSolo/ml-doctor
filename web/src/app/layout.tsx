import type { Metadata } from "next";
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/instrument-serif/400-italic.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/600.css";
import "@fontsource/jetbrains-mono/700.css";
import "./globals.css";
export const metadata: Metadata = { title: "MLDoctor — Debug the run. Prove the fix.", description: "Reproduce, investigate, patch, verify.",
  icons: { icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><rect width='16' height='16' fill='%23bc4a1a'/><text x='2' y='12' font-size='10' fill='%23ffffff'>M</text></svg>" } };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en" data-mode="dark"><body>
      <script dangerouslySetInnerHTML={{ __html: "try{var m=localStorage.getItem('mldoctor-theme');if(m!=='light'&&m!=='dark')m=window.matchMedia('(prefers-color-scheme: light)').matches?'light':'dark';document.documentElement.dataset.mode=m;}catch(e){document.documentElement.dataset.mode='dark';}" }} />
      {children}</body></html>;
}

import type { Metadata } from "next";
import { Archivo, IBM_Plex_Mono, Inter_Tight } from "next/font/google";
import "./globals.css";

/*
  Self-hosted at build time by next/font — no request to fonts.googleapis.com at runtime.
  Competition rule 4: the app must run with no internet, and the typography *is* the
  design, so a CDN fallback to system-ui would be a different product on stage.
*/

/*
  Archivo loads as a variable font with no fixed weight, because the design drives its
  width axis directly (`font-variation-settings: "wdth"`) and next/font rejects `axes`
  alongside a fixed weight. The expanded-heavy grotesk is the timing-tower voice; losing
  the axis would lose it.
*/
const archivo = Archivo({
  subsets: ["latin"],
  axes: ["wdth"],
  variable: "--font-archivo",
  display: "swap",
});

const interTight = Inter_Tight({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter-tight",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Weather Whiplash",
  description: "Live track condition detector — surface state, trend, and the pit call.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${archivo.variable} ${interTight.variable} ${plexMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}

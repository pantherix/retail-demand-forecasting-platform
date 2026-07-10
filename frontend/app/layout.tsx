import type { Metadata } from "next";
import "./globals.css";

// Use system font stack — avoids Google Fonts network fetch at Docker build time.
// The --font-inter CSS variable is consumed by globals.css with a full fallback chain.
const fontVariable = "--font-inter";

export const metadata: Metadata = {
  title: "Scuderia Retail - Demand Intelligence & Telemetry Command Center",
  description: "Advanced demand forecasting, inventory optimization, scenario simulation, and AI-powered decision support.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="h-full antialiased dark"
      style={{ [`--${fontVariable.slice(2)}` as string]: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" } as React.CSSProperties}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AIMD | AI Media Detection & Digital Forensics",
  description: "Evidence-based media analysis for synthetic content and provenance clues.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

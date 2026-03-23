import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ABM Engine",
  description: "B2B AI Agency Outreach Engine",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

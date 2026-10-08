import type { Metadata } from "next";
import "./globals.css";
import PwaRegister from "./pwa-register";
import AppShell from "./app-shell";

export const metadata: Metadata = {
  title: "LeadPitch",
  description: "Local-business discovery and sales workspace.",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><PwaRegister /><AppShell>{children}</AppShell></body>
    </html>
  );
}

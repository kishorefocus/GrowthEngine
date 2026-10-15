import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "GrowthEngine — Connected Next.js + Python + PostgreSQL Stack",
  description: "Starter template with Next.js frontend, Python FastAPI backend, and PostgreSQL database connected seamlessly.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${jetbrainsMono.variable} antialiased selection:bg-blue-500/30 selection:text-blue-200`}>
        {children}
      </body>
    </html>
  );
}

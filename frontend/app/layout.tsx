import type { Metadata } from "next";
import AuthNavBar from "@/components/AuthNavBar";
import Footer from "@/components/Footer";
import "./globals.css";

export const metadata: Metadata = {
  title: "Autonomous Vehicle Job Finder",
  description: "Explore jobs and skills in the autonomous vehicle industry.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-ink antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white"
        >
          Skip to main content
        </a>
        <AuthNavBar />
        <div id="main-content" tabIndex={-1} className="outline-none">
          {children}
        </div>
        <Footer />
      </body>
    </html>
  );
}

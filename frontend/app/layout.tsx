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
        <AuthNavBar />
        {children}
        <Footer />
      </body>
    </html>
  );
}

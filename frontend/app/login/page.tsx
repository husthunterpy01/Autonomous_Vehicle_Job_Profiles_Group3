import type { Metadata } from "next";
import LoginClient from "./login-client";

export const metadata: Metadata = { title: "Log in | AV Job Finder" };

export default function LoginPage() {
  return <LoginClient />;
}

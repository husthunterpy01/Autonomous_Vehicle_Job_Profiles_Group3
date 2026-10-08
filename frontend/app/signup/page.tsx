import type { Metadata } from "next";
import SignUpClient from "./signup-client";

export const metadata: Metadata = { title: "Sign up | AV Job Finder" };

export default function SignUpPage() {
  return <SignUpClient />;
}

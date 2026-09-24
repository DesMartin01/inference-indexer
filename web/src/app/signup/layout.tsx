import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Create your account | InferenceIndexer.ai",
  robots: { index: false, follow: true },
};

export default function SignupLayout({ children }: { children: React.ReactNode }) {
  return children;
}

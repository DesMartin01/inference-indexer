import Link from "next/link";
import { Header, Footer } from "@/components/Header";

export default function NotFound() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#0a0a0a",
        color: "#e5e5e5",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Header activePage="" />
      <div
        style={{
          flex: 1,
          maxWidth: 720,
          margin: "0 auto",
          padding: "80px 20px",
          textAlign: "center",
        }}
      >
        <p style={{ fontSize: 13, color: "#C4A038", letterSpacing: "0.12em", textTransform: "uppercase", margin: "0 0 12px" }}>
          404
        </p>
        <h1 style={{ fontSize: 30, fontWeight: 700, color: "#f2f2f2", margin: "0 0 16px" }}>
          Page not found
        </h1>
        <p style={{ fontSize: 14.5, lineHeight: 1.6, color: "#8a8a8a", maxWidth: 460, margin: "0 auto 28px" }}>
          This model or provider may have been renamed or removed. Try searching,
          or browse the latest pricing index.
        </p>
        <Link
          href="/"
          style={{
            display: "inline-block",
            fontSize: 13.5,
            color: "#C4A038",
            textDecoration: "none",
            border: "1px solid #3a3a3a",
            padding: "10px 22px",
            borderRadius: 4,
          }}
        >
          ← Back to the index
        </Link>
      </div>
      <Footer providers={71} updatedAt="" />
    </main>
  );
}
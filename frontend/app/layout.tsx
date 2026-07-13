import type { Metadata } from "next";
import "./globals.css";
import MCPNav from "../components/MCPNav";
import FoundryAccessGate from "../components/FoundryAccessGate";

export const metadata: Metadata = {
  title: "ZoidLab MCPLab",
  description: "MCP connector lab — discover, test, govern, and version Model Context Protocol connectors.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-bg text-ink">
        <MCPNav />
        <main className="mx-auto w-full max-w-[1320px] px-5">
          <FoundryAccessGate packageLabel="Foundry Package 12">{children}</FoundryAccessGate>
        </main>
        <footer className="mx-auto mt-20 w-full max-w-[1320px] border-t border-line px-5 py-8 text-[12px] text-faint">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>ZoidLab MCPLab · Foundry Package 12 · Discover, test, govern, and version MCP connectors.</span>
            <span className="flex gap-4"><a href="https://foundry.zoidlab.ai" className="hover:text-dim">Foundry</a><a href="https://zoidlab.ai" className="hover:text-dim">zoidlab.ai</a></span>
          </div>
        </footer>
      </body>
    </html>
  );
}

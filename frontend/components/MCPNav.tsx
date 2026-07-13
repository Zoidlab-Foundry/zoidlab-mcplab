"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser } from "../lib/useUser";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/connectors", label: "Connectors" },
  { href: "/tests", label: "Tests" },
];

export default function MCPNav() {
  const path = usePathname();
  const { user } = useUser();
  const active = (h: string) => (h === "/" ? path === "/" : path.startsWith(h));

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-[1320px] items-center gap-5 px-5">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-vi/15 text-[15px] text-vi shadow-glow">⧉</span>
          <span className="text-[14.5px] font-semibold tracking-tight text-ink">
            ZoidLab <span className="prism-text">MCPLab</span>
          </span>
        </Link>
        <nav className="hidden items-center gap-1 md:flex">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href}
              className={`rounded-lg px-3 py-1.5 text-[13px] transition ${active(l.href) ? "bg-panel2 text-ink" : "text-dim hover:text-ink"}`}>
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2.5">
          <span className="hidden rounded-full border border-line px-2.5 py-1 text-[11px] text-faint sm:inline">Foundry 12</span>
          <span className="rounded-full border border-vi/30 bg-vi/10 px-2.5 py-1 text-[11px] font-medium text-vi">Nyquest Pro</span>
          {user?.email && <span className="hidden max-w-[160px] truncate text-[12px] text-dim lg:inline" title={user.email}>{user.email}</span>}
        </div>
      </div>
    </header>
  );
}

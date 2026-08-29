"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const NAV_LINKS = [
  { href: "/dashboard", label: "仪表盘" },
  { href: "/resumes", label: "简历" },
  { href: "/jobs", label: "岗位 JD" },
  { href: "/matches", label: "匹配" },
  { href: "/applications", label: "投递" },
  { href: "/knowledge", label: "知识库" },
];

export default function NavBar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-zinc-900 text-sm text-white">
            AC
          </span>
          <span>AI Career Copilot</span>
        </Link>

        {user && (
          <nav className="hidden items-center gap-1 sm:flex">
            {NAV_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="rounded-md px-3 py-1.5 text-sm text-zinc-600 transition hover:bg-zinc-100 hover:text-zinc-900"
              >
                {l.label}
              </Link>
            ))}
          </nav>
        )}

        <div className="flex items-center gap-3">
          {user ? (
            <>
              <span className="hidden text-sm text-zinc-500 sm:inline">
                {user.name || user.email}
              </span>
              <button
                onClick={handleLogout}
                className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm transition hover:bg-zinc-100"
              >
                退出
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-md px-3 py-1.5 text-sm text-zinc-600 transition hover:bg-zinc-100"
              >
                登录
              </Link>
              <Link
                href="/register"
                className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm text-white transition hover:bg-zinc-700"
              >
                注册
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

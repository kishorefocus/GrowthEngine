"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useLogout, useMe } from "@/lib/hooks";
import { clearTokens } from "@/lib/api-client";
import {
  BarChart3,
  CalendarDays,
  Clapperboard,
  Globe,
  Inbox,
  LayoutDashboard,
  Lightbulb,
  Link2,
  LogOut,
  Mail,
  Rocket,
  Search,
  Settings,
  TrendingUp,
  Users,
  ChevronRight,
  Moon,
  Sun,
} from "lucide-react";
import { useTheme } from "next-themes";
import { clsx } from "clsx";

interface NavItem {
  href: string;
  icon: React.ReactNode;
  label: string;
  badge?: string;
  comingIn?: string;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/admin/dashboard", icon: <LayoutDashboard className="w-4 h-4" />, label: "Dashboard" },
  { href: "/admin/leads", icon: <Users className="w-4 h-4" />, label: "Leads" },
  { href: "/admin/campaigns", icon: <Mail className="w-4 h-4" />, label: "Campaigns" },
  { href: "/admin/inbox", icon: <Inbox className="w-4 h-4" />, label: "Inbox" },
  { href: "/admin/calendar", icon: <CalendarDays className="w-4 h-4" />, label: "Content Calendar" },
  { href: "/admin/ideas", icon: <Lightbulb className="w-4 h-4" />, label: "Ideas & Generator" },
  { href: "/admin/video", icon: <Clapperboard className="w-4 h-4" />, label: "Video Studio" },
  { href: "/admin/seo", icon: <Search className="w-4 h-4" />, label: "SEO Manager" },
  { href: "/admin/launch", icon: <Rocket className="w-4 h-4" />, label: "Launch Hub" },
  { href: "/admin/connections", icon: <Link2 className="w-4 h-4" />, label: "Connections" },
  { href: "/admin/settings", icon: <Settings className="w-4 h-4" />, label: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useLogout();
  const { data: user } = useMe();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = mounted ? theme === "dark" : true;

  const handleLogout = () => {
    clearTokens();
    document.cookie = "gr_auth=; path=/; max-age=0";
    router.push("/admin/login");
  };

  return (
    <aside className="w-60 shrink-0 h-screen sticky top-0 flex flex-col bg-[#0d0d14] border-r border-white/[0.06]">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-violet-500/20 border border-violet-500/30 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-violet-400" />
          </div>
          <div>
            <p className="text-white font-bold text-sm leading-none">GetyourclientsB2B</p>
            <p className="text-violet-400/60 text-[10px] font-mono mt-0.5">Growth Engine</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 overflow-y-auto space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          const isComingSoon = !!item.comingIn;

          return (
            <button
              key={item.href}
              onClick={() => !isComingSoon && router.push(item.href)}
              disabled={isComingSoon}
              title={isComingSoon ? `Coming in ${item.comingIn}` : item.label}
              className={clsx(
                "w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-all group",
                isActive
                  ? "bg-violet-500/15 text-violet-300 border border-violet-500/20"
                  : isComingSoon
                  ? "text-slate-600 cursor-not-allowed"
                  : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
              )}
            >
              <span className={clsx(isActive ? "text-violet-400" : isComingSoon ? "text-slate-700" : "text-slate-500 group-hover:text-slate-300")}>
                {item.icon}
              </span>
              <span className="flex-1 text-left truncate">{item.label}</span>
              {isComingSoon && (
                <span className="text-[9px] font-mono bg-white/[0.05] text-slate-600 px-1.5 py-0.5 rounded-full border border-white/[0.04] shrink-0">
                  {item.comingIn}
                </span>
              )}
              {isActive && !isComingSoon && (
                <ChevronRight className="w-3 h-3 text-violet-400/60 shrink-0" />
              )}
            </button>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="px-3 py-3 border-t border-white/[0.06] space-y-2">
        {user && (
          <div className="px-2 py-1.5 flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-violet-500/20 border border-violet-500/30 flex items-center justify-center text-violet-400 text-xs font-bold">
              {user.email[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-300 truncate">{user.email}</p>
              <p className="text-[10px] text-violet-400/70 capitalize">{user.role}</p>
            </div>
          </div>
        )}
        <div className="flex gap-1.5">
          <button
            onClick={() => setTheme(isDark ? "light" : "dark")}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs text-slate-500 hover:text-slate-300 hover:bg-white/[0.04] transition-all"
            aria-label="Toggle theme"
          >
            {isDark ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
            {isDark ? "Light" : "Dark"}
          </button>
          <button
            onClick={handleLogout}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs text-slate-500 hover:text-rose-400 hover:bg-rose-500/[0.08] transition-all"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </button>
        </div>
      </div>
    </aside>
  );
}

import Link from "next/link";
import React from "react";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Navbar */}
      <header className="sticky top-0 z-50 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition-transform">
                G
              </div>
              <span className="font-semibold text-lg tracking-tight text-white group-hover:text-cyan-400 transition-colors">
                GlobalReach
              </span>
            </Link>

            <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-400">
              <Link href="/tools/subject-line-grader" className="hover:text-cyan-400 transition-colors">
                Subject Line Grader
              </Link>
              <Link href="/tools/email-verifier" className="hover:text-cyan-400 transition-colors">
                Free Email Verifier
              </Link>
              <Link href="/alternatives/apollo/agencies" className="hover:text-cyan-400 transition-colors">
                Apollo Alternative
              </Link>
              <Link href="/find-leads/technology/austin" className="hover:text-cyan-400 transition-colors">
                Find Leads
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/admin/login"
              className="text-xs sm:text-sm font-medium text-slate-400 hover:text-white px-3 py-1.5 transition-colors"
            >
              Sign In
            </Link>
            <a
              href="https://www.getyourclientsb2b.com/signup?utm_source=public_header&utm_medium=nav&utm_campaign=growth_engine"
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-300 hover:brightness-110 transition-all shadow-md shadow-cyan-500/20 hover:shadow-cyan-500/30"
            >
              Start Free Trial
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">{children}</main>

      {/* Public Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/90 py-12 text-sm text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-md bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-bold text-xs text-white">
                G
              </div>
              <span className="font-semibold text-white">GlobalReach</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed mb-4">
              Automated B2B client acquisition engine with real-time contact verification, compliant email sequencing, and multi-channel content planning.
            </p>
            <p className="text-xs text-slate-500">
              © {new Date().getFullYear()} GlobalReach Inc. All rights reserved.
            </p>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">Free Sales Tools</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/tools/subject-line-grader" className="hover:text-cyan-400 transition-colors">
                  Cold Email Subject Line Grader
                </Link>
              </li>
              <li>
                <Link href="/tools/email-verifier" className="hover:text-cyan-400 transition-colors">
                  Single Email Deliverability Verifier
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">Popular Comparisons</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/alternatives/apollo/agencies" className="hover:text-cyan-400 transition-colors">
                  Apollo.io Alternative for Agencies
                </Link>
              </li>
              <li>
                <Link href="/alternatives/instantly/b2b-startups" className="hover:text-cyan-400 transition-colors">
                  Instantly Alternative for Startups
                </Link>
              </li>
              <li>
                <Link href="/alternatives/lemlist/sales-teams" className="hover:text-cyan-400 transition-colors">
                  Lemlist Alternative for Sales Teams
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">Platform</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <a
                  href="https://www.getyourclientsb2b.com/signup?utm_source=public_footer&utm_medium=footer&utm_campaign=growth_engine"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyan-400 transition-colors"
                >
                  Create Account
                </a>
              </li>
              <li>
                <Link href="/admin/login" className="hover:text-cyan-400 transition-colors">
                  Admin Shell
                </Link>
              </li>
              <li>
                <span className="text-slate-600">Privacy & Terms</span>
              </li>
            </ul>
          </div>
        </div>
      </footer>
    </div>
  );
}

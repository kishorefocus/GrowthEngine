"use client";

import React, { useState } from "react";
import Link from "next/link";
import { SEOPublicPage } from "@/lib/api-client";

interface SEOSection {
  heading: string;
  content: string;
}

interface SEOFaqItem {
  question: string;
  answer: string;
}

interface SEOFeatureRow {
  feature: string;
  globalreach: string;
  competitor: string;
}

interface SEOPublicPageProps {
  page: SEOPublicPage;
  breadcrumbs: Array<{ label: string; href?: string }>;
}

export function SEOPublicPageRenderer({ page, breadcrumbs }: SEOPublicPageProps) {
  const content = page.content_json || {};
  const sections: SEOSection[] = content.sections || [];
  const faqs: SEOFaqItem[] = content.faq || [];
  const compTable = content.comparison_table;
  const cta = content.cta || {
    headline: "Automate Your B2B Client Acquisition",
    subheadline: "Prospect verified leads, ensure inbox deliverability, and scale outbound.",
    button_text: "Get Started Free",
    url: "https://www.getyourclientsb2b.com/signup?utm_source=seo&utm_medium=organic&utm_campaign=programmatic",
  };

  const [openFaq, setOpenFaq] = useState<number | null>(0);

  return (
    <article className="min-h-screen">
      {/* JSON-LD Structured Data */}
      {page.schema_org && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(page.schema_org) }}
        />
      )}

      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-slate-800/80 bg-gradient-to-b from-slate-900/60 via-slate-950 to-slate-950 pt-12 pb-16">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(6,182,212,0.1),transparent_50%)] pointer-events-none" />
        
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          {/* Breadcrumbs */}
          <nav aria-label="Breadcrumb" className="mb-6 flex items-center gap-2 text-xs text-slate-400">
            {breadcrumbs.map((b, i) => (
              <React.Fragment key={i}>
                {i > 0 && <span className="text-slate-600">/</span>}
                {b.href ? (
                  <Link href={b.href} className="hover:text-cyan-400 transition-colors">
                    {b.label}
                  </Link>
                ) : (
                  <span className="text-slate-200 font-medium truncate max-w-[200px] sm:max-w-none">
                    {b.label}
                  </span>
                )}
              </React.Fragment>
            ))}
          </nav>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white mb-6 leading-tight">
            {content.h1 || page.title}
          </h1>

          <p className="text-base sm:text-lg text-slate-300 leading-relaxed mb-8">
            {content.intro || page.meta_description}
          </p>

          <div className="flex flex-wrap items-center gap-4">
            <a
              href={cta.url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 rounded-xl font-bold text-sm text-slate-950 bg-gradient-to-r from-cyan-400 via-teal-300 to-emerald-400 hover:brightness-110 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 transition-all transform hover:-translate-y-0.5"
            >
              {cta.button_text}
            </a>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Verified contact data • Zero fake testimonials • Compliance guaranteed
            </div>
          </div>
        </div>
      </section>

      {/* Main Content Sections */}
      <section className="py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          {sections.map((sec, idx) => (
            <div key={idx} className="space-y-4">
              <h2 className="text-2xl sm:text-3xl font-bold text-slate-100 tracking-tight">
                {sec.heading}
              </h2>
              <div className="text-slate-300 leading-relaxed whitespace-pre-line text-base space-y-4">
                {sec.content}
              </div>
            </div>
          ))}

          {/* Comparison Table (for alternatives) */}
          {compTable && compTable.features && compTable.features.length > 0 && (
            <div className="mt-12 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 sm:p-8 overflow-x-auto">
              <div className="mb-6">
                <h3 className="text-xl sm:text-2xl font-bold text-white mb-2">
                  Feature Comparison: GlobalReach vs {compTable.competitor_name || "Competitor"}
                </h3>
                <p className="text-sm text-slate-400">
                  Objective breakdown of workflow capabilities, contact accuracy safeguards, and multi-channel features.
                </p>
              </div>

              <table className="w-full text-left text-sm border-collapse min-w-[500px]">
                <thead>
                  <tr className="border-b border-slate-800 text-xs font-semibold uppercase text-slate-400">
                    <th className="py-3 px-4">Feature</th>
                    <th className="py-3 px-4 text-cyan-400">GlobalReach</th>
                    <th className="py-3 px-4 text-slate-400">{compTable.competitor_name || "Alternative"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {compTable.features.map((row: SEOFeatureRow, rIdx: number) => (
                    <tr key={rIdx} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-4 px-4 font-medium text-slate-200">{row.feature}</td>
                      <td className="py-4 px-4 font-semibold text-cyan-300">{row.globalreach}</td>
                      <td className="py-4 px-4 text-slate-400">{row.competitor}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* FAQ Accordion */}
          {faqs.length > 0 && (
            <div className="mt-16 border-t border-slate-800/80 pt-12">
              <h3 className="text-2xl font-bold text-white mb-8">Frequently Asked Questions</h3>
              <div className="space-y-4">
                {faqs.map((faq, fIdx) => (
                  <div
                    key={fIdx}
                    className="rounded-xl border border-slate-800/80 bg-slate-900/30 overflow-hidden"
                  >
                    <button
                      type="button"
                      onClick={() => setOpenFaq(openFaq === fIdx ? null : fIdx)}
                      className="w-full px-5 py-4 text-left flex items-center justify-between text-sm sm:text-base font-semibold text-slate-200 hover:text-cyan-400 transition-colors"
                    >
                      <span>{faq.question}</span>
                      <span className="text-slate-500 text-lg font-mono">
                        {openFaq === fIdx ? "−" : "+"}
                      </span>
                    </button>
                    {openFaq === fIdx && (
                      <div className="px-5 pb-5 text-sm text-slate-400 leading-relaxed border-t border-slate-800/40 pt-3">
                        {faq.answer}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Sticky Bottom CTA Banner */}
      <aside className="sticky bottom-0 z-40 w-full border-t border-slate-800 bg-slate-950/95 backdrop-blur-md py-4 px-4 shadow-2xl">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-center sm:text-left">
            <h4 className="text-sm font-bold text-white">{cta.headline}</h4>
            <p className="text-xs text-slate-400 hidden sm:block">{cta.subheadline}</p>
          </div>
          <a
            href={cta.url}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full sm:w-auto px-6 py-2.5 rounded-lg text-xs sm:text-sm font-bold text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-300 hover:brightness-110 shadow-md shadow-cyan-500/20 transition-all text-center"
          >
            {cta.button_text}
          </a>
        </div>
      </aside>
    </article>
  );
}

import type { Metadata } from "next";
import { seoApi } from "@/lib/api-client";
import { SEOPublicPageRenderer } from "@/components/seo-public-page";

export const revalidate = 86400; // ISR 24h

interface PageProps {
  params: {
    slug: string;
  };
}

export async function generateStaticParams() {
  try {
    const slugs = await seoApi.getPublicSlugs();
    const matches = slugs
      .filter((s) => s.startsWith("use-cases/"))
      .map((s) => ({ slug: s.replace("use-cases/", "") }));
    if (matches.length > 0) return matches;
  } catch {
    // fallback
  }

  return [
    { slug: "b2b-saas-lead-generation" },
    { slug: "agency-client-acquisition" },
    { slug: "recruiting-firm-outbound" },
  ];
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const readable = params.slug.split("-").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
  const title = `Lead Generation for ${readable} | GlobalReach`;
  const description = `Automate prospecting, email verification, and multi-channel outreach for ${readable}. Build a predictable client pipeline with GlobalReach.`;

  return {
    title,
    description,
    alternates: {
      canonical: `https://www.getyourclientsb2b.com/use-cases/${params.slug}`,
    },
    openGraph: {
      title,
      description,
      type: "website",
      url: `https://www.getyourclientsb2b.com/use-cases/${params.slug}`,
    },
  };
}

export default async function UseCasePage({ params }: PageProps) {
  const fullSlug = `use-cases/${params.slug}`;
  let page = await seoApi.getPublicPage(fullSlug);

  const readable = params.slug.split("-").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");

  if (!page) {
    page = {
      slug: fullSlug,
      title: `Lead Generation for ${readable} | GlobalReach`,
      meta_description: `Automate prospecting and outbound client acquisition for ${readable}.`,
      content_json: {
        h1: `Automated Lead Generation for ${readable}`,
        title: `Lead Generation for ${readable}`,
        intro: `Acquiring qualified B2B clients for ${readable} demands a systematic, repeatable outbound methodology. Relying solely on referrals leaves revenue vulnerable to volatility. GlobalReach provides an automated outbound engine designed to prospect decision-makers, verify emails, and schedule sequences safely.`,
        sections: [
          {
            heading: `Prospecting Intent for ${readable}`,
            content: `Finding high-value accounts requires precision firmographic targeting. By defining clear ICP parameters across headcount, tech stack, and job functions, your sales team connects only with buyers who have genuine demand.`,
          },
          {
            heading: `Delivering Messages to Primary Inboxes`,
            content: `Outbound deliverability depends on domain health and clean contact data. GlobalReach verifies MX records and syntax in real time, preventing spam traps and keeping your sender reputation high.`,
          },
          {
            heading: `Multi-Channel Touchpoints`,
            content: `Reinforce email conversations with thought leadership on LinkedIn and educational video scripts created in the Content Studio. Multi-channel touchpoints build brand credibility before discovery calls.`,
          },
        ],
        faq: [
          { question: `How fast can I launch an outreach campaign for ${readable}?`, answer: `Most teams define their ICP, import verified leads, and launch their first sequence within one afternoon.` },
          { question: `Can I connect multiple sending domains?`, answer: `Yes. GlobalReach monitors domain health across multiple sending inboxes with ramp schedules.` },
        ],
        cta: {
          headline: `Build Your ${readable} Client Pipeline`,
          subheadline: `Automate your lead discovery and outreach with GlobalReach.`,
          button_text: `Get Started Free`,
          url: `https://www.getyourclientsb2b.com/signup?utm_source=seo&utm_medium=organic&utm_campaign=use_case&utm_content=${params.slug}`,
        },
      },
      schema_org: {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "GlobalReach",
        "applicationCategory": "BusinessApplication",
      },
    };
  }

  const breadcrumbs = [
    { label: "Home", href: "/" },
    { label: "Use Cases", href: "/use-cases/b2b-saas-lead-generation" },
    { label: readable },
  ];

  return <SEOPublicPageRenderer page={page} breadcrumbs={breadcrumbs} />;
}

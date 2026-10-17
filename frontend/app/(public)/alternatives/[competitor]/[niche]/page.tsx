import type { Metadata } from "next";
import { seoApi } from "@/lib/api-client";
import { SEOPublicPageRenderer } from "@/components/seo-public-page";

export const revalidate = 86400; // ISR 24h

interface PageProps {
  params: {
    competitor: string;
    niche: string;
  };
}

export async function generateStaticParams() {
  try {
    const slugs = await seoApi.getPublicSlugs();
    const matches = slugs
      .filter((s) => s.startsWith("alternatives/"))
      .map((s) => {
        const parts = s.split("/");
        return { competitor: parts[1], niche: parts[2] };
      });
    if (matches.length > 0) return matches;
  } catch {
    // fallback
  }

  return [
    { competitor: "apollo", niche: "agencies" },
    { competitor: "instantly", niche: "b2b-startups" },
    { competitor: "lemlist", niche: "sales-teams" },
    { competitor: "lusha", niche: "recruiters" },
  ];
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const comp = params.competitor.charAt(0).toUpperCase() + params.competitor.slice(1);
  const niche = params.niche.charAt(0).toUpperCase() + params.niche.slice(1).replace(/-/g, " ");
  const title = `Best ${comp} Alternative for ${niche} | GlobalReach`;
  const description = `Compare ${comp} and GlobalReach for ${niche}. Discover feature differences, real-time MX email verification, multi-channel social studio, and transparent pricing.`;

  return {
    title,
    description,
    alternates: {
      canonical: `https://www.getyourclientsb2b.com/alternatives/${params.competitor}/${params.niche}`,
    },
    openGraph: {
      title,
      description,
      type: "website",
      url: `https://www.getyourclientsb2b.com/alternatives/${params.competitor}/${params.niche}`,
    },
  };
}

export default async function AlternativePage({ params }: PageProps) {
  const slug = `alternatives/${params.competitor}/${params.niche}`;
  let page = await seoApi.getPublicPage(slug);

  const comp = params.competitor.charAt(0).toUpperCase() + params.competitor.slice(1);
  const niche = params.niche.charAt(0).toUpperCase() + params.niche.slice(1).replace(/-/g, " ");

  if (!page) {
    page = {
      slug,
      title: `Best ${comp} Alternative for ${niche} | GlobalReach`,
      meta_description: `Objective comparison between ${comp} and GlobalReach tailored for ${niche}.`,
      content_json: {
        h1: `${comp} vs GlobalReach for ${niche}`,
        title: `Best ${comp} Alternative for ${niche}`,
        intro: `If your ${niche} team is evaluating alternatives to ${comp}, balancing database breadth with end-to-end outbound automation is essential. GlobalReach unifies verified prospecting, built-in email validation, multi-channel social planning, and campaign attribution in one engine.`,
        sections: [
          {
            heading: `Why ${niche} Teams Look Beyond ${comp}`,
            content: `While legacy data vendors offer extensive databases, teams frequently face stale email contacts, additional credit fees for verification, and complex tool switching. A unified growth engine provides higher signal prospecting with built-in deliverability checks.`,
          },
          {
            heading: `Built-in Email Verification vs Credit Burn`,
            content: `Deliverability is crucial for modern outbound. GlobalReach checks MX records, disposable domains, and role mailboxes automatically without deducting separate verification credits, protecting your sending domain from costly reputation damage.`,
          },
          {
            heading: `Multi-Channel Content Integration`,
            content: `Cold email is only one dimension of modern customer acquisition. GlobalReach includes an integrated Social Content Studio and Video Studio, helping your brand orchestrate LinkedIn, X, and YouTube touchpoints alongside targeted email sequences.`,
          },
        ],
        comparison_table: {
          competitor_name: comp,
          features: [
            { feature: "Built-in Email Verification", globalreach: "Included on every lead", competitor: "Additional credit fees" },
            { feature: "Multi-Channel Social Studio", globalreach: "Included (X, LinkedIn, Meta, YouTube)", competitor: "Not supported" },
            { feature: "Programmatic SEO Engine", globalreach: "Included engine", competitor: "Not supported" },
            { feature: "Bounce Rate Auto-Pause Safeguard", globalreach: "Automated real-time safety", competitor: "Basic alerts" },
          ],
        },
        faq: [
          { question: `Can I import leads from ${comp} into GlobalReach?`, answer: `Yes. Standard CSV imports with automatic column mapping and suppression list checks are supported.` },
          { question: `How does GlobalReach protect domain reputation?`, answer: `Through real-time MX checks, gradual ramp schedules, and automatic pausing if bounce rates exceed 5%.` },
        ],
        cta: {
          headline: `Switch to a Modern Outbound Engine`,
          subheadline: `Join ${niche} teams scaling verified outbound with GlobalReach.`,
          button_text: `Try GlobalReach Free`,
          url: `https://www.getyourclientsb2b.com/signup?utm_source=seo&utm_medium=organic&utm_campaign=alternative&utm_content=${params.competitor}_${params.niche}`,
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
    { label: "Alternatives", href: "/alternatives/apollo/agencies" },
    { label: `${comp} for ${niche}` },
  ];

  return <SEOPublicPageRenderer page={page} breadcrumbs={breadcrumbs} />;
}

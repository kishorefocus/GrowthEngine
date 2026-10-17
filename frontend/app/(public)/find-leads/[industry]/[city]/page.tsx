import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { seoApi, SEOPublicPage } from "@/lib/api-client";
import { SEOPublicPageRenderer } from "@/components/seo-public-page";

export const revalidate = 86400; // ISR 24h

interface PageProps {
  params: {
    industry: string;
    city: string;
  };
}

export async function generateStaticParams() {
  try {
    const slugs = await seoApi.getPublicSlugs();
    const matches = slugs
      .filter((s) => s.startsWith("find-leads/"))
      .map((s) => {
        const parts = s.split("/");
        return { industry: parts[1], city: parts[2] };
      });
    if (matches.length > 0) return matches;
  } catch {
    // fallback
  }

  return [
    { industry: "technology", city: "austin" },
    { industry: "real-estate", city: "miami" },
    { industry: "saas", city: "san-francisco" },
  ];
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const ind = params.industry.charAt(0).toUpperCase() + params.industry.slice(1).replace(/-/g, " ");
  const city = params.city.charAt(0).toUpperCase() + params.city.slice(1).replace(/-/g, " ");
  const title = `Find ${ind} Leads in ${city} | GlobalReach`;
  const description = `Source verified ${ind} decision-maker leads in ${city}. Automated prospecting, real-time MX email validation, and compliant multi-channel outreach.`;

  return {
    title,
    description,
    alternates: {
      canonical: `https://www.getyourclientsb2b.com/find-leads/${params.industry}/${params.city}`,
    },
    openGraph: {
      title,
      description,
      type: "website",
      url: `https://www.getyourclientsb2b.com/find-leads/${params.industry}/${params.city}`,
    },
  };
}

export default async function FindLeadsPage({ params }: PageProps) {
  const slug = `find-leads/${params.industry}/${params.city}`;
  let page = await seoApi.getPublicPage(slug);

  const ind = params.industry.charAt(0).toUpperCase() + params.industry.slice(1).replace(/-/g, " ");
  const city = params.city.charAt(0).toUpperCase() + params.city.slice(1).replace(/-/g, " ");

  if (!page) {
    // High-converting deterministic fallback
    page = {
      slug,
      title: `Find Verified ${ind} Leads in ${city} | GlobalReach`,
      meta_description: `Discover high-converting ${ind} leads in ${city}. Automated prospecting and compliant outreach.`,
      content_json: {
        h1: `Find Verified ${ind} Leads in ${city}`,
        title: `Find ${ind} Leads in ${city}`,
        intro: `Scaling client acquisition targeting ${ind} companies in ${city} requires verified decision-maker data. Manual prospecting drains sales productivity; GlobalReach provides an automated outbound engine that finds and validates contact addresses before outreach.`,
        sections: [
          {
            heading: `The ${city} ${ind} Landscape`,
            content: `The commercial market for ${ind} in ${city} is competitive and relationship-driven. Decision-makers receive numerous cold pitches daily. To achieve breakthrough engagement rates, prospecting must target verified pain points specific to local business operations.`,
          },
          {
            heading: `Real-Time Email Verification & Deliverability`,
            content: `Avoid bouncing emails and protect your primary domain reputation. GlobalReach checks syntax, domain MX records, and disposable mailboxes prior to campaign dispatch, ensuring your communications reach executive inboxes reliably.`,
          },
          {
            heading: `Automated Outreach Sequences`,
            content: `Schedule multi-touch sequences that respect recipient working hours in ${city}. Introduce natural delays and track engagement from link click to sign-up using transparent multi-touch attribution.`,
          },
        ],
        faq: [
          { question: `How accurate is the ${ind} lead data in ${city}?`, answer: `All contacts undergo real-time syntax and MX verification prior to export or send.` },
          { question: `Does GlobalReach support CAN-SPAM and GDPR?`, answer: `Yes. Automated unsubscribe token headers, suppression enforcement, and physical address footers are built-in.` },
        ],
        cta: {
          headline: `Ready to Scale Your ${ind} Outreach in ${city}?`,
          subheadline: `Find verified contacts and automate your client acquisition with GlobalReach.`,
          button_text: `Start Free Trial`,
          url: `https://www.getyourclientsb2b.com/signup?utm_source=seo&utm_medium=organic&utm_campaign=industry_city&utm_content=${params.industry}_${params.city}`,
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
    { label: "Find Leads", href: "/find-leads/technology/austin" },
    { label: `${ind} in ${city}` },
  ];

  return <SEOPublicPageRenderer page={page} breadcrumbs={breadcrumbs} />;
}

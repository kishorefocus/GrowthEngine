import { ComingSoon } from "@/components/coming-soon";

export default function SEOPage() {
  return (
    <ComingSoon
      title="SEO Manager"
      description="Generate thousands of programmatic SEO pages from templates. industry_city, alternative, use_case."
      prompt="Prompt 4"
      features={[
        "Template builder: industry_city, alternative, use_case",
        "Bulk page generation with AI-written body",
        "Quality score filtering before publish",
        "Automatic sitemap generation",
        "Published to Next.js public routes via /(public)/[slug]",
      ]}
    />
  );
}

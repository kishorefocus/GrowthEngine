import { ComingSoon } from "@/components/coming-soon";

export default function IdeasPage() {
  return (
    <ComingSoon
      title="Ideas & Generator"
      description="AI-powered content idea generation by pillar, SEO gap analysis, and one-click drafting."
      prompt="Prompt 3"
      features={[
        "Generate ideas from brand profile + SEO gap analysis",
        "Idea pillars: education, social proof, product, community",
        "One-click draft → approval → schedule flow",
        "Claims guard on every AI-generated draft",
        "Bulk generate and save to content calendar",
      ]}
    />
  );
}

import { ComingSoon } from "@/components/coming-soon";

export default function LaunchPage() {
  return (
    <ComingSoon
      title="Launch Hub"
      description="Checklists, assets, and review campaigns for Product Hunt, G2, Capterra, Reddit, and IndieHackers."
      prompt="Prompt 4"
      features={[
        "Per-platform launch checklists with asset uploads",
        "Review request campaigns to existing users",
        "Reddit and IndieHackers post drafts (posted manually)",
        "Status tracking: pending → in_progress → done",
        "Note: PH/G2/Capterra have no public posting APIs — human submits",
      ]}
    />
  );
}

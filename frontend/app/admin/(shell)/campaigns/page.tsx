import { ComingSoon } from "@/components/coming-soon";

export default function CampaignsPage() {
  return (
    <ComingSoon
      title="Email Campaigns"
      description="Multi-step sequences with AI personalization, sending windows, and full compliance."
      prompt="Prompt 2"
      features={[
        "Multi-step sequences with configurable delays",
        "AI-personalized subject + body per lead",
        "Daily sending limits and timezone-aware windows",
        "Unsubscribe link and CAN-SPAM/GDPR compliance",
        "Open, click, reply, bounce tracking",
      ]}
    />
  );
}

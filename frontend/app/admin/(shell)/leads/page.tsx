import { ComingSoon } from "@/components/coming-soon";

export default function LeadsPage() {
  return (
    <ComingSoon
      title="Lead Engine"
      description="Import, enrich, verify and segment leads by ICP. Full suppression enforcement."
      prompt="Prompt 2"
      features={[
        "ICP builder with industry, geography, titles",
        "Lead import from CSV and GlobalReach API",
        "Email verification (MX check, disposable detection)",
        "Suppression list enforcement before every send",
        "Lead status tracking: new → contacted → replied → signed_up",
      ]}
    />
  );
}

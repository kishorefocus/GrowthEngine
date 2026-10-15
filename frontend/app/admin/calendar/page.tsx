import { ComingSoon } from "@/components/coming-soon";

export default function CalendarPage() {
  return (
    <ComingSoon
      title="Content Calendar"
      description="Schedule and publish social posts across X, LinkedIn, Instagram, Facebook, and YouTube."
      prompt="Prompt 3"
      features={[
        "Visual calendar with drag-and-drop scheduling",
        "Human approval queue before every publish",
        "Official APIs: X v2, LinkedIn Posts, Meta Graph, YouTube Data",
        "UTM-tagged links on every post",
        "Published / failed / rejected status tracking",
      ]}
    />
  );
}

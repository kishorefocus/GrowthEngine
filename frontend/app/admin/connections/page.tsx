import { ComingSoon } from "@/components/coming-soon";

export default function ConnectionsPage() {
  return (
    <ComingSoon
      title="Connections"
      description="Connect social accounts via official OAuth. Tokens stored encrypted with Fernet."
      prompt="Prompt 3"
      features={[
        "X (Twitter) OAuth 2.0 PKCE",
        "LinkedIn OAuth 2.0 (company page)",
        "Meta OAuth (Instagram Business + Facebook Page)",
        "Google OAuth (YouTube + login)",
        "Token refresh management, status monitoring",
      ]}
    />
  );
}

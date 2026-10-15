import { ComingSoon } from "@/components/coming-soon";

export default function VideoPage() {
  return (
    <ComingSoon
      title="Video Studio"
      description="Plan, script, and track video projects for YouTube with AI-generated shot lists and captions."
      prompt="Prompt 3"
      features={[
        "Target keyword → script → shot list → caption pipeline",
        "YouTube title, description, and tags generator",
        "Thumbnail prompt for AI image generation",
        "Upload to R2/S3 and publish via YouTube Data API",
        "Video project status tracking",
      ]}
    />
  );
}

import { Dashboard } from "@/components/Dashboard";
import { BackgroundImageTexture } from "@/components/ui/bg-image-texture";

export default function ConsolePage() {
  return (
    <BackgroundImageTexture variant="debut-light" opacity={0.8} className="lp">
      <Dashboard />
    </BackgroundImageTexture>
  );
}

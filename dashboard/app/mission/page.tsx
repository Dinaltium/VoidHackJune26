import { MissionControl } from "@/components/mission/MissionControl";
import { BackgroundImageTexture } from "@/components/ui/bg-image-texture";

export default function MissionPage() {
  return (
    <BackgroundImageTexture variant="debut-light" opacity={0.8} className="lp">
      <MissionControl />
    </BackgroundImageTexture>
  );
}

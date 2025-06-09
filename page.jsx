import StickyNav from "../components/StickyNav";
import HeroVideo from "../components/HeroVideo";
import ProofSection from "../components/ProofSection";
import CTAFormSection from "../components/CTAFormSection";

export default function HomePage() {
  return (
    <>
      <StickyNav />
      <main className="pt-[96px]">
        <HeroVideo />
        <ProofSection />
        <CTAFormSection />
      </main>
    </>
  );
}
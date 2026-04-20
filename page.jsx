import StickyNav from "../components/StickyNav";
import Hero from "../components/HeroVideo";
import ProofSection from "../components/ProofSection";
import ScrapeSection from "../components/CTAFormSection";

export default function HomePage() {
  return (
    <>
      <StickyNav />
      <main>
        <Hero />
        <ProofSection />
        <ScrapeSection />
      </main>
    </>
  );
}
import StickyNav from "../components/StickyNav";
import HeroVideo from "../components/HeroVideo";
import ProofSection from "../components/ProofSection";
import CTAFormSection from "../components/CTAFormSection";

const SECTIONS = [
  { id: "hero", label: "Home" },
  { id: "proof", label: "Results" },
  { id: "cta", label: "Contact" },
];

export default function HomePage() {
  return (
    <>
      <StickyNav sections={SECTIONS} />
      <main className="pt-[96px]">
        <section id="hero">
          <HeroVideo />
        </section>
        <section id="proof">
          <ProofSection />
        </section>
        <section id="cta">
          <CTAFormSection />
        </section>
      </main>
    </>
  );
}

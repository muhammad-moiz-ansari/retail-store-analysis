import { PublicReveal } from "@/components/ui/PublicReveal";
import { EffectAnchor } from "@/components/ui/PointerEffect";
import styles from "../public-pages.module.css";

export default function AboutPage() {
  return (
    <main>
      <section className={`${styles.section} ${styles.aboutIntro}`} aria-labelledby="about-title">
        <h1 id="about-title" className={styles.heroTitle}>About RetailPulse</h1>
        <p className={styles.lede}>
          RetailPulse brings store-floor observations and aisle assignments together so retail teams can review customer service activity and coordinate coverage.
        </p>
        <EffectAnchor href="/#how-it-works" className={`${styles.secondary} ${styles.specular}`}>
          See how it works <span aria-hidden="true">↗</span>
        </EffectAnchor>
      </section>

      <section className={styles.section} aria-labelledby="roles-title">
        <PublicReveal>
          <h2 id="roles-title" className={styles.sectionTitle}>Two views of the store floor</h2>
          <div className={styles.cardGrid}>
            <article className={`${styles.card} ${styles.featureCard}`}>
              <h3>For managers</h3>
              <p>Review available interaction and zone activity data, then use the workspace to coordinate aisle assignments.</p>
            </article>
            <article className={`${styles.card} ${styles.featureCard}`}>
              <h3>For employees</h3>
              <p>See your own assignments and update their status during your shift.</p>
            </article>
          </div>
        </PublicReveal>
      </section>

      <section className={styles.section} aria-labelledby="contact-title">
        <PublicReveal>
          <div className={`${styles.callout} ${styles.invite}`}>
            <h2 id="contact-title" className={styles.sectionTitle}>Get in touch</h2>
            <address className="flex flex-col gap-1 not-italic">
              <EffectAnchor href="mailto:retailpulse@gmail.com" className={`${styles.textLink} ${styles.magnetic} inline-block`}>
                retailpulse@gmail.com
              </EffectAnchor>
              <span>0300-1234567</span>
            </address>
          </div>
        </PublicReveal>
      </section>
    </main>
  );
}

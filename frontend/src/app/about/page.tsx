import { PublicReveal } from "@/components/ui/PublicReveal";
import styles from "../public-pages.module.css";

export default function AboutPage() {
  return (
    <main>
      <section className={`${styles.section} ${styles.aboutIntro}`} aria-labelledby="about-title">
        <h1 id="about-title" className={styles.heroTitle}>About RetailPulse</h1>
        <p className={styles.lede}>
          RetailPulse brings store-floor observations and aisle assignments together so retail teams can review customer service activity and coordinate coverage.
        </p>
        <a href="/#how-it-works" className={styles.textLink}>See how it works <span aria-hidden="true">↗</span></a>
      </section>

      <section className={styles.section} aria-labelledby="roles-title">
        <h2 id="roles-title" className={styles.sectionTitle}>Two views of the store floor</h2>
        <div className={styles.cardGrid}>
          <article className={styles.card}>
            <h3>For managers</h3>
            <p>Review available interaction and zone activity data, then use the workspace to coordinate aisle assignments.</p>
          </article>
          <article className={styles.card}>
            <h3>For employees</h3>
            <p>See your own assignments and update their status during your shift.</p>
          </article>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="contact-title">
        <PublicReveal>
          <div className={styles.callout}>
            <h2 id="contact-title" className={styles.sectionTitle}>Get in touch</h2>
            <address className="flex flex-col gap-1 not-italic">
              <a href="mailto:retailpulse@gmail.com" className={styles.textLink}>retailpulse@gmail.com</a>
              <span>0300-1234567</span>
            </address>
          </div>
        </PublicReveal>
      </section>
    </main>
  );
}

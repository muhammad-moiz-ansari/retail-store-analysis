import Link from "next/link";
import { HomeAurora } from "@/components/ui/HomeAurora";
import { PublicReveal } from "@/components/ui/PublicReveal";
import { EffectLink, HoloPreview } from "@/components/ui/PointerEffect";
import styles from "./public-pages.module.css";

const activity = [
  { hour: "10 AM", interactions: 8 },
  { hour: "11 AM", interactions: 11 },
  { hour: "12 PM", interactions: 16 },
  { hour: "1 PM", interactions: 13 },
  { hour: "2 PM", interactions: 10 },
  { hour: "3 PM", interactions: 6 },
];

function DashboardPreview() {
  const total = activity.reduce((sum, hour) => sum + hour.interactions, 0);
  const peak = Math.max(...activity.map((hour) => hour.interactions));

  return (
    <HoloPreview className={`${styles.preview} ${styles.holo}`}>
      <figcaption className={styles.previewCaption}>
        <span className="font-heading font-bold">Store overview</span>
        <span className={styles.sample}>Sample data</span>
      </figcaption>
      <div className={styles.previewContent}>
        <div className={styles.previewRail} aria-hidden="true">
          <span className={styles.railMark}>R</span>
          <span /><span /><span />
        </div>
        <div className={styles.previewBody}>
          <dl className={styles.metrics}>
            <div><dt>Interactions</dt><dd>{total}</dd></div>
            <div><dt>Busiest hour</dt><dd>{activity.find((hour) => hour.interactions === peak)?.hour}</dd></div>
          </dl>
          <div className={styles.chart}>
            <p className="font-heading font-semibold">Interactions by hour</p>
            <ol className={styles.bars} aria-label="Sample hourly interaction counts">
              {activity.map(({ hour, interactions }) => (
                <li key={hour}>
                  <div className={styles.barTrack} aria-hidden="true">
                    <span style={{ height: `${interactions / peak * 100}%` }} />
                  </div>
                  <span className="sr-only">{interactions} interactions at </span>
                  <span>{hour}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </HoloPreview>
  );
}

export default function LandingPage() {
  return (
    <main>
      <div className={styles.heroBackdrop}>
        <div className={styles.heroAurora} aria-hidden="true"><HomeAurora interactive /></div>
        <section className={styles.hero} aria-labelledby="landing-title">
          <div className={styles.heroCopy}>
            <h1 id="landing-title" className={styles.heroTitle}>
              See where your store needs <span>attention.</span>
            </h1>
            <p className={styles.lede}>
              RetailPulse helps retail teams review customer and employee activity from camera observations and coordinate aisle assignments from the same workspace.
            </p>
            <div className={styles.actions}>
              <EffectLink href="/login" className={`${styles.primary} ${styles.specular}`}>Sign in</EffectLink>
              <a href="#how-it-works" className={styles.secondary}>See how it works <span aria-hidden="true">↓</span></a>
            </div>
          </div>
          <DashboardPreview />
        </section>
      </div>

      <section id="how-it-works" tabIndex={-1} className={styles.section} aria-labelledby="workflow-title">
        <PublicReveal>
          <h2 id="workflow-title" className={styles.sectionTitle}>From store activity to aisle assignments</h2>
          <div className={styles.cardGrid}>
            <article className={`${styles.card} ${styles.featureCard}`}>
              <h3>Review store activity</h3>
              <p>Managers can review recorded customer–employee interactions and see how activity varies across mapped areas when observation data is available.</p>
            </article>
            <article className={`${styles.card} ${styles.featureCard}`}>
              <h3>Coordinate floor coverage</h3>
              <p>Managers can review and assign aisle tasks. Employees can open their workspace to see their assignments and update task status.</p>
            </article>
          </div>
          <Link href="/compare-people" className={styles.textLink}>Process and compare people <span aria-hidden="true">↗</span></Link>
        </PublicReveal>
      </section>

      <section className={styles.section} aria-labelledby="join-title">
        <PublicReveal>
          <div className={`${styles.callout} ${styles.invite}`}>
            <div>
              <h2 id="join-title" className={styles.sectionTitle}>Have an invite?</h2>
              <p>Use your invite token to create your RetailPulse account.</p>
            </div>
            <EffectLink href="/signup" className={`${styles.primary} ${styles.magnetic}`}>Create an account</EffectLink>
          </div>
        </PublicReveal>
      </section>
    </main>
  );
}

const peopleComparisonData = require("../data/people_comparison.json");
const videoSimilarityData = require("../data/video_similarity.json");

function formatClock(seconds) {
  const safeSeconds = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  const minutes = Math.floor(safeSeconds / 60);
  const secs = Math.floor(safeSeconds % 60);
  return `${minutes}:${String(secs).padStart(2, "0")}`;
}

function formatDuration(seconds) {
  const safeSeconds = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const secs = Math.floor(safeSeconds % 60);

  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function buildDashboardData(peopleData, similarityData) {
  const totals = peopleData?.totals ?? {};
  const averages = peopleData?.averages ?? {};
  const samples = Array.isArray(peopleData?.samples) ? peopleData.samples : [];

  const footfallIn = Number(totals.video2 ?? 0);
  const footfallOut = Number(totals.video1 ?? 0);
  const netInside = footfallIn - footfallOut;
  const avgVideo2 = Number(averages.video2 ?? 0);
  const avgVideo1 = Number(averages.video1 ?? 0);
  const avgSimilarity = Number(similarityData?.avg_ssim ?? 0);
  const avgMse = Number(similarityData?.avg_mse ?? 0);

  const floorAInteractions = samples.slice(0, 3).map((sample, index) => ({
    employee: index % 2 === 0 ? "Employee A" : "Employee B",
    customer: "Customer",
    duration: formatDuration(sample.timestamp_s ?? 0),
    zone: sample.v2_count >= sample.v1_count ? "Zone 2" : "Zone 1",
    time: formatClock(sample.timestamp_s ?? 0),
  }));

  const floorBInteractions = samples.slice(3, 6).map((sample, index) => ({
    employee: index % 2 === 0 ? "Employee C" : "Employee D",
    customer: "Customer",
    duration: formatDuration(sample.timestamp_s ?? 0),
    zone: sample.v2_count >= sample.v1_count ? "Zone 4" : "Zone 3",
    time: formatClock(sample.timestamp_s ?? 0),
  }));

  const flaggedEvents = samples
    .filter((sample) => Math.abs(Number(sample.diff ?? 0)) >= 2)
    .slice(0, 3)
    .map((sample) => ({
      label: sample.verdict || "Traffic imbalance detected",
      time: formatClock(sample.timestamp_s ?? 0),
      severity: Math.abs(Number(sample.diff ?? 0)) >= 4 ? "danger" : "accent",
    }));

  const similarityPercent = Math.min(99, Math.max(25, avgSimilarity * 100));
  const crowdImbalancePercent = Math.min(96, Math.max(18, (Math.abs(avgVideo2 - avgVideo1) / Math.max(avgVideo2 + avgVideo1, 1)) * 100 + 28));
  const responseSeconds = Math.max(1, Math.min(12, Number((100 - similarityPercent) / 8 + 1).toFixed(1)));

  const peakSample = samples.reduce((peak, sample) => {
    const currentDiff = Math.abs(Number(sample.diff ?? 0));
    if (currentDiff > peak.diff) {
      return { diff: currentDiff, timestamp: sample.timestamp_s ?? 0 };
    }
    return peak;
  }, { diff: 0, timestamp: 0 });

  const summary = {
    footfallIn,
    footfallOut,
    netInside,
    avgResponse: `${responseSeconds}s`,
    avgDuration: `${Math.max(2, Math.round(avgMse / 150))}s`,
    unattended: flaggedEvents.length,
    similarityPercent,
    peakHour: peakSample.timestamp > 0 ? `${formatClock(peakSample.timestamp - 30)} – ${formatClock(peakSample.timestamp + 30)}` : "0:00 – 0:30",
    density: crowdImbalancePercent > 60 ? "High" : crowdImbalancePercent > 35 ? "Medium" : "Low",
  };

  const comparisonBars = [
    {
      label: "Traffic similarity",
      pct: Math.round(similarityPercent),
      color: "var(--color-accent)",
    },
    {
      label: "Crowd imbalance",
      pct: Math.round(crowdImbalancePercent),
      color: "var(--color-accent-soft)",
    },
  ];

  return {
    summary,
    floorAInteractions,
    floorBInteractions,
    flaggedEvents,
    comparisonBars,
  };
}

const defaultDashboardData = buildDashboardData(peopleComparisonData, videoSimilarityData);

module.exports = {
  buildDashboardData,
  defaultDashboardData,
  peopleComparisonData,
  videoSimilarityData,
};

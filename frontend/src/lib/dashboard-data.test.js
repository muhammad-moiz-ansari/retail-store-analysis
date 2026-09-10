/* eslint-disable @typescript-eslint/no-require-imports */
const test = require("node:test");
const assert = require("node:assert/strict");
const { buildDashboardData } = require("./dashboard-data.js");

test("buildDashboardData uses backend analysis values", () => {
  const data = buildDashboardData(
    {
      totals: { video1: 57, video2: 169 },
      averages: { video1: 1.24, video2: 3.67 },
      samples: [
        { sample: 1, timestamp_s: 0, frame: 0, v1_count: 1, v2_count: 1, diff: 0, verdict: "Equal" },
        { sample: 2, timestamp_s: 1.2, frame: 30, v1_count: 2, v2_count: 4, diff: -2, verdict: "V1 needs +2" },
        { sample: 3, timestamp_s: 2.4, frame: 60, v1_count: 3, v2_count: 5, diff: -2, verdict: "V1 needs +2" },
      ],
    },
    {
      avg_ssim: 0.8765,
      avg_mse: 706.27,
      common_duration_s: 55.1,
    }
  );

  assert.equal(data.summary.footfallIn, 169);
  assert.equal(data.summary.footfallOut, 57);
  assert.equal(data.summary.netInside, 112);
  assert.equal(data.flaggedEvents[0].severity, "accent");
  assert.ok(data.comparisonBars[0].pct > 80);
});

export type EvidenceCitation = {
  id: string;
  title: string;
  period: string;
  text: string;
};

export type PosAssistantAnswer = {
  answer: string;
  citations: EvidenceCitation[];
};

export const POS_EVIDENCE: EvidenceCitation[] = [
  {
    id: "EV-KPI-2026-08-W4",
    title: "Store KPI Summary",
    period: "21 Aug 2026 to 28 Aug 2026",
    text: "Net revenue was Rs. 184,320 from 168 completed sale transactions. Average basket value was Rs. 1,097 and gross sold units were 724.",
  },
  {
    id: "EV-CONV-2026-08-W4",
    title: "Purchase Conversion",
    period: "21 Aug 2026 to 28 Aug 2026",
    text: "Purchase conversion was 68.0%, calculated as 168 completed sale transactions divided by 247 entrance events from the entrance camera.",
  },
  {
    id: "EV-SKU-MAGGI-2026-08-W4",
    title: "Maggi Noodles Performance",
    period: "21 Aug 2026 to 28 Aug 2026",
    text: "Maggi Noodles sold 168 units, generated Rs. 30,240 revenue, and held 54.2% share inside the instant noodles comparison group.",
  },
  {
    id: "EV-SKU-KNORR-2026-08-W4",
    title: "Knorr Noodles Performance",
    period: "21 Aug 2026 to 28 Aug 2026",
    text: "Knorr Noodles sold 142 units, generated Rs. 28,400 revenue, and held 45.8% share inside the instant noodles comparison group.",
  },
  {
    id: "EV-REC-COKE-2026-08-W4",
    title: "Coca-Cola 500ml Recommendation",
    period: "Run generated 28 Aug 2026",
    text: "Coca-Cola 500ml is RESTOCK. On hand is 18 units, lead time is 7 days, safety stock is 24 units, and the 7-day forecast is 96 units. Suggested order quantity is 102.",
  },
  {
    id: "EV-REC-LAYS-2026-08-W4",
    title: "Lay's Classic Recommendation",
    period: "Run generated 28 Aug 2026",
    text: "Lay's Classic is MONITOR. Forecast confidence is low because only 29 complete sales-history days are available, so no strong inventory action is recommended.",
  },
  {
    id: "EV-REC-WATER-2026-08-W4",
    title: "Nestle Water Recommendation",
    period: "Run generated 28 Aug 2026",
    text: "Nestle Water 1.5L is HOLD. Stock covers 39 forecast days and comparable demand declined by 23% versus the previous equal-length period.",
  },
  {
    id: "EV-QUALITY-2026-08-W4",
    title: "Data Quality Flags",
    period: "21 Aug 2026 to 28 Aug 2026",
    text: "No zero-footfall periods were detected. Hourly conversion is shown with a visit-timing caveat because a visitor may enter before purchasing later.",
  },
];

function pickEvidence(query: string) {
  const normalized = query.toLowerCase();
  if (normalized.includes("restock") || normalized.includes("recommend") || normalized.includes("hold") || normalized.includes("inventory")) {
    return POS_EVIDENCE.filter((item) => item.id.includes("REC"));
  }
  if (normalized.includes("conversion") || normalized.includes("footfall") || normalized.includes("entry") || normalized.includes("entrance")) {
    return POS_EVIDENCE.filter((item) => item.id.includes("CONV") || item.id.includes("QUALITY"));
  }
  if (normalized.includes("compare") || normalized.includes("maggi") || normalized.includes("knorr") || normalized.includes("product") || normalized.includes("sku") || normalized.includes("top")) {
    return POS_EVIDENCE.filter((item) => item.id.includes("SKU"));
  }
  if (normalized.includes("quality") || normalized.includes("missing") || normalized.includes("zero")) {
    return POS_EVIDENCE.filter((item) => item.id.includes("QUALITY"));
  }
  return POS_EVIDENCE.filter((item) => item.id.includes("KPI") || item.id.includes("CONV") || item.id.includes("REC-COKE"));
}

export function answerPosQuestion(query: string): PosAssistantAnswer {
  const evidence = pickEvidence(query);
  const normalized = query.toLowerCase();

  if (normalized.includes("restock") || normalized.includes("recommend") || normalized.includes("hold") || normalized.includes("inventory")) {
    return {
      answer: "Coca-Cola 500ml is the strongest RESTOCK candidate because projected demand plus safety stock exceeds current stock. Nestle Water 1.5L is a temporary HOLD because stock covers more than 30 forecast days while demand is declining. Lay's Classic should stay MONITOR because the forecast history is too short for a strong action.",
      citations: evidence,
    };
  }

  if (normalized.includes("conversion") || normalized.includes("footfall") || normalized.includes("entry") || normalized.includes("entrance")) {
    return {
      answer: "Purchase conversion is 68.0% for the selected demo period. It is calculated as completed sale transactions divided by entrance events, so it is a transaction-to-entry ratio rather than proof that 68% of unique visitors purchased.",
      citations: evidence,
    };
  }

  if (normalized.includes("compare") || normalized.includes("maggi") || normalized.includes("knorr")) {
    return {
      answer: "Maggi Noodles is leading the instant noodles comparison group with 168 units and 54.2% share. Knorr Noodles follows with 142 units and 45.8% share, so the dummy trend shows Maggi ahead by 26 units this week.",
      citations: evidence,
    };
  }

  if (normalized.includes("top") || normalized.includes("product") || normalized.includes("sku")) {
    return {
      answer: "The top demo SKU is Maggi Noodles at 168 units, followed by Knorr Noodles at 142 units. Coca-Cola 500ml is important operationally because it is flagged RESTOCK despite not being the top revenue item.",
      citations: evidence,
    };
  }

  return {
    answer: "For the demo period, POS performance is healthy: Rs. 184,320 net revenue, 168 completed sale transactions, Rs. 1,097 average basket value, and 68.0% purchase conversion. The main inventory action is to restock Coca-Cola 500ml, monitor Lay's Classic, and temporarily hold Nestle Water 1.5L.",
    citations: evidence,
  };
}


export type PosRecommendationStatus = "RESTOCK" | "MONITOR" | "HOLD";

export type PosAnalytics = {
  run_id: string | null;
  dataset_version: string;
  period: { from: string; to: string };
  horizon: 7 | 30;
  currency: "PKR";
  timezone: string;
  generated_at: string;
  quality_flags: string[];
  kpis: {
    gross_sales: number;
    refunds: number;
    net_revenue: number;
    gross_sold_units: number;
    net_units: number;
    distinct_sale_transactions: number;
    average_basket_value: number;
    items_per_basket: number;
    margin: number | null;
    margin_status: "complete" | "partial" | "unavailable";
  };
  products: Array<{
    sku_id: string;
    sku_name: string;
    category: string;
    gross_units: number;
    net_units: number;
    net_revenue: number;
    gross_revenue: number;
    transaction_count: number;
    sales_velocity_units_per_day: number;
    unit_share: number;
  }>;
  categories: Array<{ category: string; net_revenue: number; share: number }>;
  conversion: {
    entries: number;
    transactions: number;
    conversion: number | null;
    flags: string[];
    buckets: Array<{ period: string; entries: number; transactions: number; conversion: number | null }>;
    definition: string;
  };
  forecasts: Record<string, {
    model: string;
    status: string;
    confidence: "high" | "medium" | "low";
    history_days: number;
    total_units: number;
    forecast_units: number[];
    validation: Record<string, { wape: number | null; mae: number; cutoffs: number }>;
  }>;
  recommendations: Array<{
    sku_id: string;
    sku_name: string;
    status: PosRecommendationStatus;
    confidence: "high" | "medium" | "low";
    rule: string;
    suggested_order_qty: number;
    snapshot_at?: string;
    on_hand?: number;
    lead_time_days?: number;
    safety_stock_units?: number;
    coverage_days?: number;
    warnings?: string[];
  }>;
  anomalies: Array<{ scope: string; scope_id: string; severity: string; message: string }>;
};

export type PosQueryAnswer = {
  answer: string;
  mode: "structured" | "extractive" | "insufficient_evidence";
  citations: Array<{ id: string; period: { from: string; to: string }; text: string; scope_type: string; scope_id: string }>;
};


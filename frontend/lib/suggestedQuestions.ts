// Curated incantations per database. Phase 4 ships Northwind only.

export interface SuggestedQuestion {
  id: string;
  text: string;
  hint: string; // a one-word vibe to display under the question
}

export const SUGGESTED_QUESTIONS: Record<string, SuggestedQuestion[]> = {
  northwind: [
    {
      id: "discontinued-count",
      text: "How many products are discontinued?",
      hint: "scalar",
    },
    {
      id: "top-customers",
      text: "Top 5 customers by number of orders.",
      hint: "ranking",
    },
    {
      id: "category-revenue",
      text: "Top 5 product categories by total revenue.",
      hint: "revenue",
    },
    {
      id: "monthly-2017",
      text: "Show monthly order count for the year 2017.",
      hint: "time",
    },
    {
      id: "shipper-share",
      text: "What share of all orders does each shipper handle?",
      hint: "share",
    },
    {
      id: "fuller-reports",
      text: "Which employees report to Andrew Fuller?",
      hint: "hierarchy",
    },
    {
      id: "avg-shipping-days",
      text: "What is the average number of days between order and shipped date?",
      hint: "duration",
    },
    {
      id: "loyal-customers",
      text: "Which customers have placed more than 10 orders?",
      hint: "loyalty",
    },
  ],
};

export interface DemoDatabase {
  id: string;
  name: string;
  blurb: string;
  tableCount: number;
}

export const DEMO_DATABASES: DemoDatabase[] = [
  {
    id: "northwind",
    name: "Northwind",
    blurb: "Classic e-commerce — orders, customers, suppliers.",
    tableCount: 13,
  },
];

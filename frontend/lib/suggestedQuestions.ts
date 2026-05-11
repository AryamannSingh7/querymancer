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

  hr: [
    {
      id: "hr-headcount-by-dept",
      text: "How many active employees does each department have?",
      hint: "distribution",
    },
    {
      id: "hr-avg-salary-by-dept",
      text: "What is the average current salary in each department?",
      hint: "ranking",
    },
    {
      id: "hr-top-managers",
      text: "Which 5 managers have the most direct reports?",
      hint: "hierarchy",
    },
    {
      id: "hr-sick-days-by-dept",
      text: "Which department has used the most approved sick days?",
      hint: "scalar",
    },
    {
      id: "hr-top-pto",
      text: "Who are the top 5 employees by total approved PTO days taken?",
      hint: "ranking",
    },
    {
      id: "hr-rating-trend",
      text: "How did average performance ratings compare between 2023 and 2024 across departments?",
      hint: "time",
    },
    {
      id: "hr-salary-growth",
      text: "Which active employees have seen the biggest salary increase since their hire date?",
      hint: "loyalty",
    },
    {
      id: "hr-top-earners-per-dept",
      text: "Who are the top 3 earners in each department right now?",
      hint: "ranking",
    },
    {
      id: "hr-payroll-vs-budget",
      text: "How does each department's total payroll compare to its budget?",
      hint: "share",
    },
    {
      id: "hr-over-band",
      text: "Which employees are currently paid above their job title's salary band maximum?",
      hint: "scalar",
    },
  ],

  ipl: [
    {
      id: "ipl-total-sixes",
      text: "How many sixes were hit across all IPL matches in the dataset?",
      hint: "scalar",
    },
    {
      id: "ipl-team-wins",
      text: "How many matches did each team win across all seasons?",
      hint: "distribution",
    },
    {
      id: "ipl-top-run-scorers",
      text: "Who are the top 5 run-scorers across all seasons?",
      hint: "ranking",
    },
    {
      id: "ipl-purple-cap-per-season",
      text: "Which bowler took the most wickets in each IPL season?",
      hint: "ranking",
    },
    {
      id: "ipl-sixes-per-season",
      text: "How did the total number of sixes hit change season by season from 2020 to 2024?",
      hint: "time",
    },
    {
      id: "ipl-mi-vs-csk",
      text: "What is the all-time head-to-head record between Mumbai Indians and Chennai Super Kings?",
      hint: "head-to-head",
    },
    {
      id: "ipl-economy-leaders",
      text: "Which 5 bowlers have the best economy rate among those who have bowled at least 40 overs?",
      hint: "ranking",
    },
    {
      id: "ipl-top-batter-per-team",
      text: "Who is the highest run-scorer for each franchise across all seasons?",
      hint: "distribution",
    },
    {
      id: "ipl-toss-advantage",
      text: "Does winning the toss actually help? Show the win rate for teams that won the toss versus chose to bat or field.",
      hint: "share",
    },
    {
      id: "ipl-qualified-strike-rate",
      text: "Which 5 batters have the highest career strike rate among those who have faced at least 200 balls?",
      hint: "ranking",
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
  {
    id: "hr",
    name: "HR",
    blurb: "People org — employees, salaries, reviews, time-off.",
    tableCount: 7,
  },
  {
    id: "ipl",
    name: "IPL",
    blurb: "Cricket — matches, players, batting & bowling stats.",
    tableCount: 8,
  },
];

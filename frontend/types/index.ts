export type Action = "REVIEW" | "ARCHIVE" | "PASS" | "ERROR"
export type Confidence = "High" | "Medium" | "Low"

export interface DealSummary {
  id: string
  company: string
  sector: string | null
  stage: string | null
  hq: string | null
  fit_pct: number | null
  action: Action
  confidence: Confidence | null
  bonus_pts: number
  deck_name: string
  created_at: string
}

export interface DimensionScore {
  score: number
  reasoning: string
}

export interface BonusPoints {
  renowned_vc_backers: boolean
  clear_path_to_profitability: boolean
  repeat_founder: boolean
}

export interface DealBreakers {
  pre_product_pre_revenue: boolean
  hardware_business_model: boolean
  d2c_consumer_ecommerce: boolean
}

export interface ClaimCheck {
  claim: string
  category: string
  status: "verified" | "unverified" | "contradicted"
  source: string | null
  source_url: string | null
  confidence: string
  notes: string
}

export interface SearchResult {
  title: string
  url: string
  content: string
  score: number
}

export interface SearchLog {
  query: string
  results: SearchResult[]
}

export interface Claims {
  startup_name: string
  hq_location: string | null
  market: {
    tam: string | null
    problem: string | null
    competition: string[]
    tailwinds: string[]
  }
  product: {
    solution: string | null
    moat: string | null
  }
  business_model: {
    model_type: string | null
    arr: string | null
    arr_growth: string | null
    num_customers: string | null
    gross_margin: string | null
    pricing: string | null
    gtm: string | null
  }
  team: {
    ceo: string | null
    cofounders: string[]
    domain_expertise: boolean | null
    serial_entrepreneur: boolean | null
    notable_investors: string[]
  }
  investment: {
    series: string | null
    ask_usd: string | null
    post_money_valuation: string | null
    use_of_funds: string | null
    runway: string | null
  }
  missing_info: string[]
}

export interface ThesisResult {
  sector_fit: DimensionScore
  geography_fit: DimensionScore
  stage_fit: DimensionScore
  arr_traction_fit: DimensionScore
  overall_fit: number
  confidence: Confidence
  missing_data_points: string[]
  bonus_points: BonusPoints
  action: Action
  action_reasoning: string
}

export interface FactResult {
  fact_checks: ClaimCheck[]
  deal_breakers: DealBreakers
  red_flags: string[]
  overall_credibility: string
}

export interface Memo {
  startup_name: string
  overall_fit: number
  action: Action
  confidence: string
  thesis_score_table: string
  deal_breaker_status: string
  bonus_points_summary: string
  summary_business: string
  summary_market: string
  summary_unit_econ: string
  summary_traction: string
  summary_product: string
  summary_team: string
  top_3_risks: string[]
  reasons_to_invest: string[]
  reasons_to_pass: string[]
  founder_questions: string[]
  recommended_next_step: string
}

export interface DealDetail extends DealSummary {
  claims_json: Claims | null
  fact_json: FactResult | null
  thesis_json: ThesisResult | null
  memo_json: Memo | null
  search_logs: SearchLog[]
  slide_texts: Array<{ slide_num: number; text: string; is_image_based: boolean }>
  errors_json: Record<string, string>
}

export interface ProgressEvent {
  type: "progress" | "done" | "error"
  message?: string
  deal_id?: string
}

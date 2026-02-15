export type ClarificationPolicy = {
    max_questions?: number;
    allow_proceed_with_assumptions?: boolean;
  };
  
  export type ClarificationQuestion = {
    id: string;
    question: string;
    required?: boolean;
    affects?: string[];
    default_assumption?: string | null;
  };
  
  export type DraftLogFrame = {
    goal: string;
    purpose: string;
    outcomes: string[];
    inputs: string[];
    user_answers?: Record<string, string> | null;
  };
  
  export type DraftEngineOutput = {
    draft_lfo: DraftLogFrame;
    confidence: number;
    open_questions: string[];
    mapping?: any;
  };
  
  export type ClarificationOutput = {
    question_set: ClarificationQuestion[];
    stop_condition: string[];
    next_action: "wait_for_user" | "proceed_with_assumptions";
  };
  
  export type DraftResponse = {
    drafting: DraftEngineOutput;
    clarification: ClarificationOutput;
    preprocess: any;
  };
  
  export type RefineRequest = {
    raw_text: string;
    draft_lfo: DraftLogFrame;
    question_set: ClarificationQuestion[];
    answers: Record<string, string>;
    policy?: ClarificationPolicy;
  };
  
  export type RefineResponse = {
    drafting: DraftEngineOutput;
    clarification: ClarificationOutput;
    preprocess: any;
  };
  
  export type LfoLevel = "goal" | "purpose" | "outcome" | "input";
  export type Severity = "info" | "warn" | "error";
  
  export type StatementRef = {
    level: LfoLevel;
    index: number;
    text: string;
  };
  
  export type ObjectiveFinding = {
    type: string;              // keep string for now; you can tighten to union later
    severity: Severity;
    message: string;
    statement: StatementRef;
    evidence?: Record<string, number>;
  };
  
  export type ObjectiveRecommendedEdit = {
    statement: StatementRef;
    action: "relabel" | "split" | "rewrite" | "delete_duplicate";
    to_level?: LfoLevel | null;
    replacement_texts?: string[] | null;
    rationale: string;
  };
  
  export type ObjectiveScores = {
    structure_integrity: number; // 0..1
    by_level?: Partial<Record<LfoLevel, number>>;
  };
  
  export type ObjectiveClassification = {
    findings: ObjectiveFinding[];
    recommended_edits: ObjectiveRecommendedEdit[];
    scores: ObjectiveScores;
  };
  
  export type ObjectiveClassifierRequest = {
    lfo: DraftLogFrame;
    context?: Record<string, any> | null;
    policy?: Record<string, any> | null;
  };
  
  export type ObjectiveClassifierResponse = {
    classification: ObjectiveClassification;
  };  

export type CausalFinding = {
  type: string;
  severity: Severity;
  message: string;
  from_statement?: StatementRef | null;
  to_statement?: StatementRef | null;
  evidence?: Record<string, number>;
};

export type CausalRewriteSuggestion = {
  target: StatementRef;
  suggested_text: string;
  rationale: string;
};

export type CausalScores = {
  causal_logic: number;
  by_link?: Record<string, number>;
};

export type CausalLogicAnalysis = {
  findings: CausalFinding[];
  rewrite_suggestions: CausalRewriteSuggestion[];
  scores: CausalScores;
};

export type CausalLogicRequest = {
  lfo: DraftLogFrame;
  context?: Record<string, any> | null;
  policy?: Record<string, any> | null;
};

export type CausalLogicResponse = {
  analysis: CausalLogicAnalysis;
};
  
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  
  async function postJson<T>(path: string, body: any): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`API error ${res.status} ${res.statusText}\n${text}`);
    }
    return (await res.json()) as T;
  }
  
  export const api = {
    draft: (text: string) => postJson<DraftResponse>("/draft", { text }),
    refine: (req: RefineRequest) => postJson<RefineResponse>("/refine", req),
    classifyObjectives: (req: ObjectiveClassifierRequest) => postJson<ObjectiveClassifierResponse>("/classify-objectives", req),
  analyzeCausalLogic: (req: CausalLogicRequest) => postJson<CausalLogicResponse>("/causal-logic", req),
  };
  
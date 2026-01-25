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
  };
  
"use client";

import { useMemo, useState } from "react";
import { api, type ClarificationQuestion, type DraftLogFrame, type DraftResponse, type RefineResponse } from "./apiClient";

type ApiResult = DraftResponse | RefineResponse;

function pretty(obj: any) {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

export default function Page() {
  const [rawText, setRawText] = useState(
    "We want to reduce onboarding time for new engineers on our lab software team. Today it takes ~6 weeks before someone can ship code."
  );

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [result, setResult] = useState<ApiResult | null>(null);

  // answers keyed by question id
  const [answers, setAnswers] = useState<Record<string, string>>({});

  const drafting = (result as any)?.drafting;
  const draftLfo: DraftLogFrame | null = drafting?.draft_lfo ?? null;

  const clarification = (result as any)?.clarification ?? null;
  const questionSet: ClarificationQuestion[] = clarification?.question_set ?? [];

  const blocked = clarification?.next_action === "wait_for_user";

  // reset answers when new questions appear (but keep existing if ids overlap)
  useMemo(() => {
    if (!questionSet?.length) return;
    setAnswers((prev) => {
      const next: Record<string, string> = { ...prev };
      for (const q of questionSet) {
        if (next[q.id] === undefined) next[q.id] = "";
      }
      // drop removed question ids
      for (const k of Object.keys(next)) {
        if (!questionSet.some((q) => q.id === k)) delete next[k];
      }
      return next;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionSet.map((q) => q.id).join("|")]);

  async function onGenerate() {
    setLoading(true);
    setError(null);
    try {
      const r = await api.draft(rawText);
      setResult(r);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onRefine() {
    if (!draftLfo) return;
    setLoading(true);
    setError(null);
    try {
      // send only non-empty answers
      const compactAnswers: Record<string, string> = {};
      for (const [k, v] of Object.entries(answers)) {
        if (v?.trim()) compactAnswers[k] = v.trim();
      }

      const r = await api.refine({
        raw_text: rawText,
        draft_lfo: draftLfo,
        question_set: questionSet,
        answers: compactAnswers,
        policy: { max_questions: 3, allow_proceed_with_assumptions: true },
      });
      setResult(r);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif", padding: 16 }}>
      <h1 style={{ margin: "0 0 12px 0" }}>LogFrame Designer</h1>

      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 12 }}>
        <button onClick={onGenerate} disabled={loading} style={btnStyle}>
          {loading ? "Working..." : "Generate first draft"}
        </button>

        <button
          onClick={onRefine}
          disabled={loading || !draftLfo || questionSet.length === 0}
          style={btnStyle}
          title={questionSet.length === 0 ? "No questions to answer." : "Apply answers and refine draft"}
        >
          {loading ? "Working..." : "Refine with answers"}
        </button>

        {drafting?.confidence !== undefined && (
          <div style={{ position: "relative", display: "inline-block" }}>
            <span style={{ fontSize: 13, opacity: 0.8 }}>
              Confidence{" "}
              <span
                style={{
                  cursor: "help",
                  borderBottom: "1px dotted #999",
                }}
              >
                ⓘ
              </span>
              : <b>{Number(drafting.confidence).toFixed(2)}</b>
            </span>

            <div className="confidence-tooltip">
              <div style={{ fontWeight: 600, marginBottom: 4 }}>
                Draft completeness
              </div>
              <div>
                Shows how clear and well-specified this LogFrame is based on missing
                details and open questions.
              </div>
              <div style={{ marginTop: 6, opacity: 0.85 }}>
                This does not judge whether the idea is good.
              </div>
            </div>
          </div>

        )}

        {clarification?.next_action && (
          <span style={{ fontSize: 13, opacity: 0.8 }}>
            Next action: <b>{clarification.next_action}</b>
          </span>
        )}
      </div>

      {error && (
        <div style={{ padding: 12, background: "#ffecec", border: "1px solid #ffb3b3", borderRadius: 8, marginBottom: 12 }}>
          <b>Error</b>
          <pre style={{ whiteSpace: "pre-wrap", margin: "8px 0 0 0" }}>{error}</pre>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        {/* Intake */}
        <section style={cardStyle}>
          <h2 style={h2Style}>Intake</h2>
          <p style={pStyle}>Describe the initiative in plain language.</p>
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            rows={14}
            style={{
              width: "100%",
              borderRadius: 8,
              border: "1px solid #ddd",
              padding: 10,
              fontSize: 14,
              resize: "vertical",
            }}
          />
          <div style={{ marginTop: 10, fontSize: 12, opacity: 0.75 }}>
            Tip: include who/where/why + any metrics or timeframe you already know.
          </div>
        </section>

        {/* Questions */}
        <section style={cardStyle}>
          <h2 style={h2Style}>Clarification</h2>
          {result === null ? (
            <p style={pStyle}>Generate a first draft to see questions.</p>
          ) : questionSet.length === 0 ? (
            <p style={pStyle}>No clarification questions right now.</p>
          ) : (
            <>
              <p style={pStyle}>
                Answer what you can. Required questions are marked. Then click <b>Refine with answers</b>.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {questionSet.map((q) => (
                  <div key={q.id} style={{ padding: 10, border: "1px solid #eee", borderRadius: 8 }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
                      <div style={{ fontWeight: 700 }}>{q.question}</div>
                      {q.required && (
                        <span style={{ position: "relative", display: "inline-block" }} className="required-badge-wrap">
                          <span
                            style={{
                              fontSize: 12,
                              padding: "2px 6px",
                              borderRadius: 999,
                              border: "1px solid #ccc",
                              cursor: "help",
                              userSelect: "none",
                            }}
                            aria-label="Required question"
                            title="" // prevents default browser tooltip
                          >
                            required ⓘ
                          </span>

                          <span className="required-tooltip">
                            <div style={{ fontWeight: 600, marginBottom: 4 }}>Required question</div>
                            <div>
                              Marked required when the question asks for key missing details like <b>timeframe</b>,{" "}
                              <b>measurement/metrics</b>, or <b>who is responsible</b>.
                            </div>
                            <div style={{ marginTop: 6, opacity: 0.85 }}>
                              The assistant pauses until required questions are answered.
                            </div>
                          </span>
                        </span>
                      )}
                    </div>

                    {q.default_assumption && (
                      <div style={{ fontSize: 12, opacity: 0.75, marginTop: 4 }}>
                        Default assumption: {q.default_assumption}
                      </div>
                    )}

                    <input
                      value={answers[q.id] ?? ""}
                      onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                      placeholder="Type your answer..."
                      style={{
                        marginTop: 8,
                        width: "100%",
                        borderRadius: 8,
                        border: "1px solid #ddd",
                        padding: 10,
                        fontSize: 14,
                      }}
                    />
                  </div>
                ))}
              </div>

              {blocked && (
                <div style={{ marginTop: 10, fontSize: 12, opacity: 0.8 }}>
                  The assistant is waiting for required answers before proceeding.
                </div>
              )}
            </>
          )}
        </section>

        {/* Draft */}
        <section style={cardStyle}>
          <h2 style={h2Style}>Draft</h2>
          {result === null ? (
            <p style={pStyle}>Your draft will appear here.</p>
          ) : (
            <>
              <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 8 }}>
                Goal / Purpose / Outcomes / Inputs (JSON for now)
              </div>
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  background: "#fafafa",
                  border: "1px solid #eee",
                  borderRadius: 8,
                  padding: 10,
                  fontSize: 12,
                  maxHeight: 520,
                  overflow: "auto",
                }}
              >
                {pretty(draftLfo ?? drafting)}
              </pre>
            </>
          )}
        </section>
      </div>

      <div style={{ marginTop: 14, fontSize: 12, opacity: 0.7 }}>
        Backend endpoints used: <code>/draft</code> and <code>/refine</code> (FastAPI).
      </div>
    </main>
  );
}

const btnStyle: React.CSSProperties = {
  padding: "10px 12px",
  borderRadius: 10,
  border: "1px solid #ccc",
  background: "white",
  cursor: "pointer",
};

const cardStyle: React.CSSProperties = {
  border: "1px solid #eee",
  borderRadius: 12,
  padding: 12,
  boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
  minHeight: 380,
};

const h2Style: React.CSSProperties = {
  margin: "0 0 8px 0",
  fontSize: 16,
};

const pStyle: React.CSSProperties = {
  margin: "0 0 10px 0",
  fontSize: 13,
  opacity: 0.85,
};

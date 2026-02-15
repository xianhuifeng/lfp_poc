"use client";

import { useMemo, useState } from "react";
import {
  api,
  type AmendmentSuggestion,
  type ClarificationQuestion,
  type StatementRef,
  type DraftLogFrame,
  type DraftResponse,
  type RefineResponse,
  type ObjectiveClassification,
  type CausalLogicAnalysis,
  type Severity,
} from "./apiClient";

type ApiResult = DraftResponse | RefineResponse;
type SuggestionStatus = "pending" | "applied" | "dismissed";
type SuggestionSource = "structure" | "causal" | "amendment";
type AmendmentHistoryItem = { text: string; createdAt: string; count: number };

type ReviewSuggestion = {
  id: string;
  source: SuggestionSource;
  severity: Severity;
  target: StatementRef;
  currentText: string;
  suggestedText: string;
  rationale: string;
};

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
  const [sourceLocked, setSourceLocked] = useState(false);
  const [amendmentText, setAmendmentText] = useState("");
  const [amendmentSuggestions, setAmendmentSuggestions] = useState<AmendmentSuggestion[]>([]);
  const [amendmentHistory, setAmendmentHistory] = useState<AmendmentHistoryItem[]>([]);

  const [result, setResult] = useState<ApiResult | null>(null);
  const [editableDraft, setEditableDraft] = useState<DraftLogFrame | null>(null);
  const [suggestionStatus, setSuggestionStatus] = useState<Record<string, SuggestionStatus>>({});

  // answers keyed by question id
  const [answers, setAnswers] = useState<Record<string, string>>({});
  // classification of objectives
  const [classification, setClassification] = useState<ObjectiveClassification | null>(null);
  const [causalLogic, setCausalLogic] = useState<CausalLogicAnalysis | null>(null);


  const drafting = (result as any)?.drafting;
  const draftLfo: DraftLogFrame | null = drafting?.draft_lfo ?? null;
  const activeDraft: DraftLogFrame | null = editableDraft ?? draftLfo;

  const clarification = (result as any)?.clarification ?? null;
  const questionSet: ClarificationQuestion[] = clarification?.question_set ?? [];

  const blocked = clarification?.next_action === "wait_for_user";
  const hasCausalErrors = (causalLogic?.findings ?? []).some(f => f.severity === "error");

  function getStatementText(draft: DraftLogFrame | null, target: StatementRef): string | null {
    if (!draft) return null;
    if (target.level === "goal") return draft.goal ?? null;
    if (target.level === "purpose") return draft.purpose ?? null;
    if (target.level === "outcome") return draft.outcomes?.[target.index] ?? null;
    if (target.level === "input") return draft.inputs?.[target.index] ?? null;
    return null;
  }

  function applyRewriteToDraft(draft: DraftLogFrame, target: StatementRef, newText: string): DraftLogFrame | null {
    const next: DraftLogFrame = {
      ...draft,
      outcomes: [...(draft.outcomes ?? [])],
      inputs: [...(draft.inputs ?? [])],
    };
    if (target.level === "goal") {
      next.goal = newText;
      return next;
    }
    if (target.level === "purpose") {
      next.purpose = newText;
      return next;
    }
    if (target.level === "outcome") {
      if (target.index < 0 || target.index >= next.outcomes.length) return null;
      next.outcomes[target.index] = newText;
      return next;
    }
    if (target.level === "input") {
      if (target.index < 0 || target.index >= next.inputs.length) return null;
      next.inputs[target.index] = newText;
      return next;
    }
    return null;
  }

  const reviewSuggestions: ReviewSuggestion[] = useMemo(() => {
    const out: ReviewSuggestion[] = [];
    const baseDraft = activeDraft;

    for (const [idx, edit] of (classification?.recommended_edits ?? []).entries()) {
      const suggested = edit.replacement_texts?.[0];
      if (!suggested) continue; // v1: only rewrite-like suggestions with a single preview text
      const current = getStatementText(baseDraft, edit.statement) ?? edit.statement.text;
      out.push({
        id: `structure-${idx}-${edit.statement.level}-${edit.statement.index}`,
        source: "structure",
        severity: "warn",
        target: edit.statement,
        currentText: current,
        suggestedText: suggested,
        rationale: edit.rationale,
      });
    }

    for (const [idx, suggestion] of (causalLogic?.rewrite_suggestions ?? []).entries()) {
      const current = getStatementText(baseDraft, suggestion.target) ?? suggestion.target.text;
      out.push({
        id: `causal-${idx}-${suggestion.target.level}-${suggestion.target.index}`,
        source: "causal",
        severity: "warn",
        target: suggestion.target,
        currentText: current,
        suggestedText: suggestion.suggested_text,
        rationale: suggestion.rationale,
      });
    }

    for (const suggestion of amendmentSuggestions) {
      const current = getStatementText(baseDraft, suggestion.target) ?? suggestion.current_text;
      out.push({
        id: suggestion.id,
        source: "amendment",
        severity: "warn",
        target: suggestion.target,
        currentText: current,
        suggestedText: suggestion.suggested_text,
        rationale: suggestion.rationale,
      });
    }

    return out;
  }, [classification, causalLogic, amendmentSuggestions, activeDraft]);

  const pendingSuggestions = reviewSuggestions.filter((s) => (suggestionStatus[s.id] ?? "pending") === "pending");

  async function runChecksForDraft(lfo: DraftLogFrame) {
    try {
      const res = await api.classifyObjectives({ lfo });
      setClassification(res.classification);
    } catch {
      setClassification(null);
    }
    try {
      const res = await api.analyzeCausalLogic({ lfo });
      setCausalLogic(res.analysis);
    } catch {
      setCausalLogic(null);
    }
  }

  function keepSuggestion(suggestion: ReviewSuggestion) {
    const base = activeDraft;
    if (!base) return;
    const latestCurrent = getStatementText(base, suggestion.target);
    if (latestCurrent !== null && latestCurrent !== suggestion.currentText) {
      setError("This suggestion is stale because the target text changed. Re-run checks first.");
      return;
    }
    const updated = applyRewriteToDraft(base, suggestion.target, suggestion.suggestedText);
    if (!updated) {
      setError("Unable to apply suggestion: invalid target location.");
      return;
    }
    setEditableDraft(updated);
    setSuggestionStatus((prev) => ({ ...prev, [suggestion.id]: "applied" }));
  }

  function cancelSuggestion(suggestion: ReviewSuggestion) {
    setSuggestionStatus((prev) => ({ ...prev, [suggestion.id]: "dismissed" }));
  }

  function startNewInitiative() {
    setResult(null);
    setEditableDraft(null);
    setSuggestionStatus({});
    setAnswers({});
    setClassification(null);
    setCausalLogic(null);
    setError(null);
    setSourceLocked(false);
    setAmendmentText("");
    setAmendmentSuggestions([]);
    setAmendmentHistory([]);
  }

  async function onGenerateAmendmentSuggestions() {
    if (!activeDraft) return;
    const text = amendmentText.trim();
    if (!text) return;
    setLoading(true);
    setError(null);
    try {
      const out = await api.amendDraft({
        raw_text: rawText,
        amendment_text: text,
        draft_lfo: activeDraft,
      });
      setAmendmentSuggestions(out.suggestions);
      setAmendmentHistory((prev) => [
        { text, createdAt: new Date().toISOString(), count: out.suggestions.length },
        ...prev,
      ].slice(0, 8));
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }


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
      setSuggestionStatus({});
      setAmendmentSuggestions([]);

      // classify objectives after generating a draft
      const lfo = (r as any)?.drafting?.draft_lfo;
      if (lfo) {
        setSourceLocked(true);
        setEditableDraft(lfo);
        await runChecksForDraft(lfo);
      }

    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onRefine() {
    if (!activeDraft) return;
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
        draft_lfo: activeDraft,
        question_set: questionSet,
        answers: compactAnswers,
        policy: { max_questions: 3, allow_proceed_with_assumptions: true },
      });
      setResult(r);
      setSuggestionStatus({});
      setAmendmentSuggestions([]);

      // classify objectives after refining the draft
      const lfo = (r as any)?.drafting?.draft_lfo;
      if (lfo) {
        setEditableDraft(lfo);
        await runChecksForDraft(lfo);
      }

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
          disabled={loading || !activeDraft || questionSet.length === 0}
          style={btnStyle}
          title={questionSet.length === 0 ? "No questions to answer." : "Apply answers and refine draft"}
        >
          {loading ? "Working..." : "Refine with answers"}
        </button>

        <button
          onClick={() => activeDraft && runChecksForDraft(activeDraft)}
          disabled={loading || !activeDraft}
          style={btnStyle}
          title="Re-run structure and causal checks for the current draft"
        >
          Re-run checks
        </button>

        <button
          onClick={startNewInitiative}
          disabled={loading || !sourceLocked}
          style={btnStyle}
          title="Start a new initiative and unlock the source paragraph"
        >
          Start new initiative
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
            disabled={sourceLocked}
            rows={14}
            style={{
              width: "100%",
              borderRadius: 8,
              border: "1px solid #ddd",
              padding: 10,
              fontSize: 14,
              resize: "vertical",
              background: sourceLocked ? "#f7f7f7" : "white",
              opacity: sourceLocked ? 0.85 : 1,
            }}
          />
          <div style={{ marginTop: 10, fontSize: 12, opacity: 0.75 }}>
            {sourceLocked
              ? "Source is locked after first draft generation. Continue by refining the LogFrame, or click 'Start new initiative' to unlock and begin a fresh run."
              : "Tip: include who/where/why + any metrics or timeframe you already know."}
          </div>
          {sourceLocked && (
            <div style={{ marginTop: 12, padding: 10, border: "1px solid #eee", borderRadius: 8, background: "#fcfcfc" }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Propose amendment</div>
              <textarea
                value={amendmentText}
                onChange={(e) => setAmendmentText(e.target.value)}
                placeholder="What changed since original brief? e.g. timeline shortened to 8 weeks, new approver added..."
                rows={5}
                style={{
                  width: "100%",
                  borderRadius: 8,
                  border: "1px solid #ddd",
                  padding: 10,
                  fontSize: 13,
                  resize: "vertical",
                }}
              />
              <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                <button
                  style={btnStyle}
                  onClick={onGenerateAmendmentSuggestions}
                  disabled={loading || !activeDraft || !amendmentText.trim()}
                  title="Generate targeted rewrite suggestions from amendment text"
                >
                  Generate amendment suggestions
                </button>
                <button
                  style={btnStyle}
                  onClick={() => {
                    setAmendmentText("");
                    setAmendmentSuggestions([]);
                  }}
                  disabled={loading || (!amendmentText && amendmentSuggestions.length === 0)}
                >
                  Clear
                </button>
              </div>
              {amendmentHistory.length > 0 && (
                <div style={{ marginTop: 8, fontSize: 12, opacity: 0.75 }}>
                  Last amendment: {amendmentHistory[0].count} suggestion(s) generated.
                </div>
              )}
            </div>
          )}
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
              {classification && (
                <div style={{ marginBottom: 10, padding: 10, border: "1px solid #eee", borderRadius: 10, background: "#fcfcff" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ fontWeight: 700 }}>Structure integrity</div>
                    <div style={{ fontSize: 13 }}>
                      <b>{Number(classification.scores.structure_integrity).toFixed(2)}</b>
                    </div>
                  </div>

                  {/* Blocked */}
                  {(() => {
                    const hasErrors = classification.findings.some((f) => f.severity === "error");
                    return (
                      <div style={{ marginTop: 10, marginBottom: 10 }}>
                        {hasErrors ? (
                          <div style={{ padding: 10, borderRadius: 10, border: "1px solid #ffb3b3", background: "#ffecec" }}>
                            <b>Blocked:</b> Structural issues found. Fix errors to proceed.
                          </div>
                        ) : (
                          <div style={{ padding: 10, borderRadius: 10, border: "1px solid #cfe8cf", background: "#effaf0" }}>
                            <b>OK:</b> Structure looks good enough to proceed.
                          </div>
                        )}
                      </div>
                    );
                  })()}

                  {/* Findings */}
                  <div style={{ marginTop: 8, fontSize: 12, opacity: 0.85 }}>
                    {classification.findings?.length ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        {classification.findings.slice(0, 6).map((f, idx) => (
                          <div key={idx} style={{ padding: 8, border: "1px solid #f0f0f0", borderRadius: 8 }}>
                            <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
                              <span style={{ fontWeight: 700 }}>{f.severity.toUpperCase()}</span>
                              <span style={{ opacity: 0.7 }}>{f.type}</span>
                            </div>
                            <div style={{ marginTop: 4 }}>{f.message}</div>
                            <div style={{ marginTop: 4, opacity: 0.7 }}>
                              {f.statement.level}[{f.statement.index}]: {f.statement.text}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div>No structural issues detected.</div>
                    )}
                  </div>

                  {/* Recommended edits */}
                  {classification.recommended_edits?.length ? (
                    <div style={{ marginTop: 10 }}>
                      <div style={{ fontWeight: 700, marginBottom: 6 }}>Recommended edits</div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {classification.recommended_edits.map((e, idx) => (
                          <div key={idx} style={{ padding: 8, border: "1px solid #eee", borderRadius: 8, fontSize: 12 }}>
                            <div>
                              <b>{e.action}</b>
                              {e.to_level ? ` → ${e.to_level}` : ""}
                            </div>
                            <div style={{ opacity: 0.8, marginTop: 4 }}>
                              {e.statement.level}[{e.statement.index}]: {e.statement.text}
                            </div>
                            <div style={{ opacity: 0.75, marginTop: 4 }}>{e.rationale}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              )}

              {causalLogic && (
                <div style={{ marginBottom: 10, padding: 10, border: "1px solid #eee", borderRadius: 10, background: "#fffdfb" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ fontWeight: 700 }}>Causal logic</div>
                    <div style={{ fontSize: 13 }}>
                      <b>{Number(causalLogic.scores.causal_logic).toFixed(2)}</b>
                    </div>
                  </div>

                  <div style={{ marginTop: 10, marginBottom: 10 }}>
                    {hasCausalErrors ? (
                      <div style={{ padding: 10, borderRadius: 10, border: "1px solid #ffb3b3", background: "#ffecec" }}>
                        <b>Flagged:</b> Critical causal issues found.
                      </div>
                    ) : (
                      <div style={{ padding: 10, borderRadius: 10, border: "1px solid #cfe8cf", background: "#effaf0" }}>
                        <b>Advisory:</b> Causal logic checks completed (warning-first mode).
                      </div>
                    )}
                  </div>

                  <div style={{ marginTop: 8, fontSize: 12, opacity: 0.85 }}>
                    {causalLogic.findings?.length ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        {causalLogic.findings.slice(0, 6).map((f, idx) => (
                          <div key={idx} style={{ padding: 8, border: "1px solid #f0f0f0", borderRadius: 8 }}>
                            <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
                              <span style={{ fontWeight: 700 }}>{f.severity.toUpperCase()}</span>
                              <span style={{ opacity: 0.7 }}>{f.type}</span>
                            </div>
                            <div style={{ marginTop: 4 }}>{f.message}</div>
                            {f.from_statement && (
                              <div style={{ marginTop: 4, opacity: 0.7 }}>
                                {f.from_statement.level}[{f.from_statement.index}]: {f.from_statement.text}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div>No causal gaps detected.</div>
                    )}
                  </div>
                </div>
              )}

              {activeDraft && (
                <div style={{ marginBottom: 10, padding: 10, border: "1px solid #eee", borderRadius: 10, background: "#fbfbfb" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ fontWeight: 700 }}>Suggestion review</div>
                    <div style={{ fontSize: 12, opacity: 0.8 }}>
                      Pending: <b>{pendingSuggestions.length}</b>
                    </div>
                  </div>

                  {pendingSuggestions.length === 0 ? (
                    <div style={{ marginTop: 8, fontSize: 12, opacity: 0.8 }}>No pending suggestions.</div>
                  ) : (
                    <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                      {pendingSuggestions.slice(0, 8).map((s) => (
                        <div key={s.id} style={{ border: "1px solid #eee", borderRadius: 8, padding: 8 }}>
                          <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 4 }}>
                            {s.source} • {s.target.level}[{s.target.index}]
                          </div>
                          <div style={{ fontSize: 12, color: "#b42318", background: "#fef3f2", border: "1px solid #fecaca", borderRadius: 6, padding: 6 }}>
                            - {s.currentText}
                          </div>
                          <div style={{ marginTop: 6, fontSize: 12, color: "#067647", background: "#ecfdf3", border: "1px solid #a6f4c5", borderRadius: 6, padding: 6 }}>
                            + {s.suggestedText}
                          </div>
                          <div style={{ marginTop: 6, fontSize: 12, opacity: 0.75 }}>{s.rationale}</div>
                          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                            <button style={btnStyle} onClick={() => cancelSuggestion(s)} disabled={loading}>
                              Cancel
                            </button>
                            <button style={btnStyle} onClick={() => keepSuggestion(s)} disabled={loading}>
                              Keep
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

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
                {pretty(activeDraft ?? drafting)}
              </pre>
            </>
          )}
        </section>
      </div>

      <div style={{ marginTop: 14, fontSize: 12, opacity: 0.7 }}>
        Backend endpoints used: <code>/draft</code>, <code>/refine</code>, <code>/classify-objectives</code>, <code>/causal-logic</code>, and <code>/amend-draft</code>.
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

import { useEffect, useState } from "react";
import type { TFunction } from "i18next";
import { Trans } from "react-i18next";
import type { Case, Prediction, Result } from "./types";
import { useFormat, useTranslation } from "./i18n";
import { errorText, familyLabel, packLabel, slug } from "./labels";
import { CaseState } from "./Guide";
import { useViewState } from "./ViewHistory";
import savedAnalysis from "../../../docs/evidence/video-task-analysis.json";
import findings from "../../../docs/evidence/video-findings.json";

export type CaseJump = { pack: string; family: string; model?: string; search?: string };
type Counts = { n: number; planned: number; label_correct: number; strict_correct: number;
  label_accuracy: number | null; strict_accuracy: number | null; failed: number; invalid: number;
  unsupported: number; missing: number; p50_ms: number | null; p95_ms: number | null };
type Group = { key: string; pack: string; family: string; cases: number; reference_n: number;
  shared_n: number; teacher_n: number; models: Record<string, Record<string, Counts>> };
type Analysis = { run_id: string; groups: Group[]; models: string[]; shared_reference_n: number };
type Facet = { pack: string; family: string; count: number };
type CaseIndex = { total: number; cases: (Case & { preview: string })[]; facets: Facet[] };
// Descriptive question-type names live in explore.types.<slug>; other names fall back to the pack/family label.
const title = (t: TFunction, pack: string, family: string) =>
  family ? t(`explore.types.${slug(family)}`, { defaultValue: familyLabel(t, family) })
    : pack ? t(`explore.types.${slug(pack)}`, { defaultValue: packLabel(t, pack) })
      : t("explore.allQuestionTypes");
const cache = new Map<string, unknown>();
async function read<T>(path: string, signal: AbortSignal, immutable: boolean): Promise<T> {
  if (immutable && cache.has(path)) return cache.get(path) as T;
  const r = await fetch(`/api${path}`, { signal });
  if (!r.ok) {
    const d = await r.json();
    if (!d.detail) throw Object.assign(new Error(`Request failed (${r.status})`), { key: "explore.errors.requestFailed", params: { status: r.status } });
    throw Object.assign(new Error(d.detail), { code: d.code, params: d.params });
  }
  const data = await r.json();
  if (immutable) { if (cache.size >= 60) cache.delete(cache.keys().next().value!); cache.set(path, data); }
  return data;
}

export function TaskAnalysis({ result, onCases }: { result: Result; onCases: (jump: CaseJump) => void }) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const [data, setData] = useState<Analysis | null>(null), [error, setError] = useState<unknown>(null);
  const [groupKey, setGroupKey] = useViewState(`analysis:${result.run_id}:group`, "::"), [model, setModel] = useViewState(`analysis:${result.run_id}:model`, "");
  const [scope, setScope] = useViewState(`analysis:${result.run_id}:scope`, "shared"), [metric, setMetric] = useViewState(`analysis:${result.run_id}:metric`, "label");
  useEffect(() => {
    const abort = new AbortController(); setData(null); setError(null);
    if (window.__ARENA_REPORT__) {
      if (result.run_id === savedAnalysis.run_id) setData(savedAnalysis as Analysis);
      else setError(Object.assign(new Error("Open the local Arena app to explore question types for this saved report."), { key: "explore.errors.reportAnalysis" }));
    } else read<Analysis>(`/runs/${result.run_id}/analysis`, abort.signal, result.status === "complete")
      .then(d => { if (!abort.signal.aborted) setData(d); }).catch(e => { if (!abort.signal.aborted) setError(e); });
    return () => abort.abort();
  }, [result.run_id, result.status]);
  const group = data?.groups.find(g => g.key === groupKey) || data?.groups[0];
  const noSharedQuestions = !!group?.reference_n && !group.shared_n;
  const activeScope = group?.reference_n === 0 && group.teacher_n ? "teacher" : noSharedQuestions && scope === "shared" ? "supported" : scope;
  const rows = result.entrants.filter(e => !model || e.id === model).map(e => ({ ...e, counts: group?.models[e.id]?.[activeScope] }))
    .filter(e => e.counts).sort((a, b) => ((b.counts![`${metric}_accuracy` as keyof Counts] as number | null) ?? -1) - ((a.counts![`${metric}_accuracy` as keyof Counts] as number | null) ?? -1));
  const lead = rows[0], leadScore = lead?.counts?.[`${metric}_accuracy` as keyof Counts] as number | null | undefined;
  const scopeNote = !group ? "" : activeScope === "teacher" ? t("explore.analysis.teacherScope", { n: fmt.number(group.teacher_n) })
    : activeScope === "shared" ? t("explore.analysis.sharedScope", { shared: fmt.number(group.shared_n), excluded: fmt.number(group.reference_n - group.shared_n) })
      : t("explore.analysis.supportedScope", { n: fmt.number(group.reference_n) });
  return <section className="task-analysis" aria-label={t("explore.analysis.title")}>
    <div className="section-title"><div><h2>{t("explore.analysis.title")}</h2><p>{t("explore.analysis.intro")}</p></div></div>
    {error != null && <p role="alert">{errorText(t, error)}</p>}{!data && error == null && <p role="status">{t("explore.analysis.loading")}</p>}
    {data && group && <>
      <div className="quick-types" aria-label={t("explore.jumpToType")}>{[["", ""], ["Classification", "AG News"], ["Classification", "SST-2"], ["Classification", "BANKING77"], ["Multilingual", "XNLI"], ["Arena Fresh", ""], ["RAG relevance", "SciFact"]].filter(([p, f]) => data.groups.some(g => g.key === `${p}::${f}`)).map(([p, f]) => <button key={p+f} aria-pressed={group.key === `${p}::${f}`} className={group.key === `${p}::${f}` ? "selected" : ""} onClick={() => setGroupKey(group.key === `${p}::${f}` ? "::" : `${p}::${f}`)}>{title(t, p, f)}</button>)}</div>
      <div className="abcd-controls">
        <label>{t("explore.questionType")}<select value={group.key} onChange={e => setGroupKey(e.target.value)}>{data.groups.map(g => <option key={g.key} value={g.key}>{g.family ? "↳ " : ""}{title(t, g.pack, g.family)} · {fmt.number(g.cases)}</option>)}</select></label>
        <label>{t("explore.model")}<select value={model} onChange={e => setModel(e.target.value)}><option value="">{t("explore.analysis.compareAll", { n: fmt.number(result.entrants.length) })}</option>{result.entrants.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}</select></label>
        <label>{t("explore.analysis.questionSet")}<select value={activeScope} onChange={e => setScope(e.target.value)} disabled={!group.reference_n}><option value="shared" disabled={noSharedQuestions}>{noSharedQuestions ? t("explore.analysis.scopes.sharedNone") : t("explore.analysis.scopes.shared")}</option><option value="supported">{t("explore.analysis.scopes.supported")}</option>{!group.reference_n && <option value="teacher">{t("explore.analysis.scopes.teacher")}</option>}</select></label>
        <label>{t("explore.analysis.score")}<select value={metric} onChange={e => setMetric(e.target.value)}><option value="label">{t("explore.analysis.metrics.label")}</option><option value="strict">{t("explore.analysis.metrics.strict")}</option></select></label>
      </div>
      <div className="analysis-scope"><div className="scope-heading"><h3>{title(t, group.pack, group.family)}</h3>{leadScore != null && <div className="leading-score"><strong>{fmt.percent(leadScore, 2)}</strong><span>{model ? lead.name : t("explore.analysis.highestScore", { name: lead.name })}</span></div>}</div><p>{scopeNote} {group.teacher_n > 0 && activeScope !== "teacher" ? t("explore.analysis.teacherExcluded", { n: fmt.number(group.teacher_n) }) : ""}</p>
        <button className="text-button" onClick={() => onCases({ pack: group.pack, family: group.family, model })}>{t("explore.analysis.openQuestions")}</button></div>
      {noSharedQuestions && <p className="score-note">{t("explore.analysis.noSharedQuestions")}</p>}
      {result.run_id === findings.run_id && group.family === "BANKING77" && <p className="slice-insight">{t("explore.insights.banking77")}</p>}
      {result.run_id === findings.run_id && group.family === "AG News" && <p className="slice-insight"><Trans i18nKey="explore.insights.agNews" components={{ link: <button className="text-button" onClick={() => onCases({pack:group.pack,family:group.family,search:"classification-ag news-450"})}/> }}/></p>}
      {result.run_id === findings.run_id && group.family === "SciFact" && <div className="slice-insight"><h3>{t("explore.insights.scifactTitle")}</h3><p>{t("explore.insights.scifactIntro")}</p><div className="table-scroll"><table className="task-ranking"><thead><tr><th>{t("explore.model")}</th><th>{t("explore.insights.relevantFound")}</th><th>{t("explore.insights.irrelevantPassed")}</th><th>{t("explore.insights.yesPrecision")}</th></tr></thead><tbody>{Object.entries(findings.relevance).filter(([id])=>model ? id===model : ["jev","winnow","decider","laya","uniform"].includes(id)).map(([id,r])=><tr key={id}><td>{result.entrants.find(e=>e.id===id)?.name || id}</td><td>{fmt.number(r.positive.correct)} / {fmt.number(r.positive.n)}</td><td>{fmt.number(r.confusion.find(c=>c.gold==="no"&&c.selected==="yes")?.n || 0)}</td><td>{r.positive_precision == null ? t("common.unavailable") : fmt.percent(r.positive_precision, 2)}</td></tr>)}</tbody></table></div><p className="small muted">{t("explore.insights.scifactNote")}</p></div>}
      <div className="table-scroll"><table className="task-ranking"><thead><tr><th>{t("explore.model")}</th><th>{activeScope === "teacher" ? t("explore.table.agreement") : t("explore.table.accuracy")}</th><th>{activeScope === "teacher" ? t("explore.table.matchesScored") : t("explore.table.correctScored")}</th><th>{activeScope === "teacher" ? t("explore.table.nonMatches") : t("explore.table.notCorrect")}</th><th>{t("explore.failedOutput")}</th><th>{t("explore.table.coverage")}</th><th>{t("explore.table.qualityLatency")}</th><th>{t("explore.table.evidence")}</th></tr></thead><tbody>{rows.map((e, i) => {
        const c = e.counts!, value = c[`${metric}_accuracy` as keyof Counts] as number | null;
        const coverage = group.models[e.id][activeScope === "teacher" ? "teacher" : "supported"];
        const correct = metric === "label" ? c.label_correct : c.strict_correct;
        const unavailable = coverage.unsupported === coverage.planned && coverage.planned > 0 ? t("explore.unsupported") : coverage.missing === coverage.planned && coverage.planned > 0 ? t("explore.table.notRun") : t("explore.table.noScored");
        return <tr key={e.id} className={i === 0 && value != null && !model ? "leading-row" : ""}><td>{e.name}</td><td><strong>{value == null ? unavailable : fmt.percent(value, 2)}</strong>{value != null && <span className="table-bar"><i style={{ width: `${value * 100}%` }}/></span>}</td><td>{c.n ? `${fmt.number(correct)} / ${fmt.number(c.n)}` : "—"}</td><td>{c.n ? fmt.number(c.n - correct) : "—"}</td><td>{c.n ? <>{fmt.number(c.failed)} <small>{t("explore.table.invalidIncluded", { n: fmt.number(c.invalid) })}</small></> : "—"}</td><td>{t("explore.table.attempted", { n: fmt.number(coverage.n), planned: fmt.number(coverage.planned) })}<small>{t("explore.table.coverageGaps", { unsupported: fmt.number(coverage.unsupported), missing: fmt.number(coverage.missing) })}</small></td><td>{fmt.duration(c.p50_ms)} / {fmt.duration(c.p95_ms)}</td><td><button className="text-button" onClick={() => onCases({ pack: group.pack, family: group.family, model: e.id })}>{t("explore.table.inspect")}</button></td></tr>;
      })}</tbody></table></div>
      <p className="small muted">{activeScope === "teacher" ? t("explore.analysis.teacherFootnote") : t("explore.analysis.scoredFootnote")}</p>
      <p className="small muted">{t("explore.analysis.sortingNote")}</p>
    </>}
  </section>;
}

export function EvidenceExplorer({ rid, result }: { rid: string | null; result: Result | null }) {
  const [filters, setFilters] = useViewState(`cases:${rid}:filters`, { pack: "", family: "", model: "", kind: "", outcome: "", search: "", offset: 0 });
  const [search, setSearch] = useViewState(`cases:${rid}:search`, ""), [index, setIndex] = useState<CaseIndex | null>(null);
  const [chosen, setChosen] = useViewState(`cases:${rid}:chosen`, ""), [detail, setDetail] = useState<{ case: Case; predictions: Prediction[] } | null>(null);
  const { t } = useTranslation();
  const fmt = useFormat();
  const [error, setError] = useState<unknown>(null), [loading, setLoading] = useState(false), [reveal, setReveal] = useState(false);
  const immutable = result?.status === "complete";
  const change = (patch: Partial<typeof filters>) => { setFilters(f => ({ ...f, ...patch, offset: 0 })); setChosen(""); setDetail(null); };
  useEffect(() => { const timer = setTimeout(() => setFilters(f => f.search === search ? f : { ...f, search, offset: 0 }), 250); return () => clearTimeout(timer); }, [search]);
  useEffect(() => {
    if (!rid || window.__ARENA_REPORT__) return;
    const abort = new AbortController(); setLoading(true); setError(null); setDetail(null);
    const q = new URLSearchParams({ ...filters, offset: String(filters.offset), limit: "30", index_only: "true" });
    read<CaseIndex>(`/runs/${rid}/cases?${q}`, abort.signal, immutable).then(d => {
      if (abort.signal.aborted) return; setIndex(d); setChosen(old => d.cases.some(c => c.id === old) ? old : d.cases[0]?.id || ""); setLoading(false);
    }).catch(e => { if (!abort.signal.aborted) { setError(e); setLoading(false); } });
    return () => abort.abort();
  }, [rid, filters, immutable]);
  useEffect(() => {
    if (!rid || !chosen || loading || window.__ARENA_REPORT__) return;
    const abort = new AbortController(); setDetail(null); setReveal(false);
    read<{ case: Case; predictions: Prediction[] }>(`/runs/${rid}/cases/${encodeURIComponent(chosen)}${filters.model ? `?model=${encodeURIComponent(filters.model)}` : ""}`, abort.signal, immutable)
      .then(d => { if (!abort.signal.aborted) setDetail(d); }).catch(e => { if (!abort.signal.aborted) setError(e); });
    return () => abort.abort();
  }, [rid, chosen, filters.model, loading, immutable]);
  if (window.__ARENA_REPORT__) return <p>{t("explore.cases.reportOnly")}</p>;
  if (!rid) return <p>{t("explore.cases.chooseRun")}</p>;
  const c = detail?.case, facets = index?.facets || [], packs = [...new Set(facets.map(f => f.pack))];
  return <><div className="explorer-controls abcd-controls">
    <label>{t("explore.jumpToType")}<select value={`${filters.pack}::${filters.family}`} onChange={e => { const [pack, family] = e.target.value.split("::"); change({ pack, family }); }}><option value="::">{t("explore.allQuestionTypes")}</option>{packs.map(p => <optgroup key={p} label={packLabel(t, p)}><option value={`${p}::`}>{t("explore.cases.allOfType", { name: title(t, p, "") })}</option>{facets.filter(f => f.pack === p).map(f => <option key={f.family} value={`${p}::${f.family}`}>{title(t, p, f.family)} · {fmt.number(f.count)}</option>)}</optgroup>)}</select></label>
    <label>{t("explore.model")}<select value={filters.model} onChange={e => change({ model: e.target.value, outcome: "" })}><option value="">{t("explore.cases.allResponses")}</option>{result?.entrants.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}</select></label>
    <label>{t("explore.cases.outcome")}<select value={filters.outcome} disabled={!filters.model} onChange={e => change({ outcome: e.target.value })}><option value="">{t("explore.cases.allOutcomes")}</option><option value="correct">{t("explore.cases.outcomes.correct")}</option><option value="wrong">{t("explore.cases.outcomes.wrong")}</option><option value="failed">{t("explore.failedOutput")}</option><option value="unsupported">{t("explore.unsupported")}</option></select></label>
    <label>{t("explore.cases.answerFormat")}<select value={filters.kind} onChange={e => change({ kind: e.target.value })}><option value="">{t("explore.cases.allFormats")}</option><option value="choice">{t("explore.cases.formats.choice")}</option><option value="noul">{t("explore.cases.formats.noul")}</option><option value="score">{t("explore.cases.formats.score")}</option></select></label>
  </div>{error != null && <p role="alert">{errorText(t, error)}</p>}<div className="case-workspace">
    <aside className="case-list"><div className="search"><input aria-label={t("explore.cases.searchLabel")} placeholder={t("explore.cases.searchPlaceholder")} value={search} onChange={e => setSearch(e.target.value)}/></div>
      <p className="small muted" role="status">{loading ? t("explore.cases.loadingQuestions") : t("explore.matchingQuestions", { count: index?.total || 0, n: fmt.number(index?.total || 0) })}</p>
      <div className="case-list-items" aria-busy={loading}>{index?.cases.map(item => <button key={item.id} disabled={loading} className={chosen === item.id ? "selected" : ""} onClick={() => setChosen(item.id)}><span>{title(t, item.pack, item.family)}<small>{item.preview}</small><small>{item.id}</small></span></button>)}</div>
      <div className="pagination"><button disabled={loading || !filters.offset} onClick={() => setFilters(f => ({ ...f, offset: Math.max(0, f.offset - 30) }))}>{t("explore.cases.previous")}</button><span>{t("common.pageRange", { from: fmt.number(index?.total ? filters.offset + 1 : 0), to: fmt.number(Math.min(filters.offset + 30, index?.total || 0)), total: fmt.number(index?.total || 0) })}</span><button disabled={loading || filters.offset + 30 >= (index?.total || 0)} onClick={() => setFilters(f => ({ ...f, offset: f.offset + 30 }))}>{t("explore.cases.next")}</button></div>
      {!!index?.total && <label className="page-jump">{t("explore.cases.page")}<select aria-label={t("explore.cases.jumpToPage")} value={Math.floor(filters.offset / 30)} onChange={e => setFilters(f => ({ ...f, offset: Number(e.target.value) * 30 }))}>{Array.from({ length: Math.ceil(index.total / 30) }, (_, i) => <option key={i} value={i}>{fmt.number(i + 1)}</option>)}</select></label>}
    </aside><section className="case-detail" aria-busy={loading || (!!chosen && !detail)}>{c ? <>
      <div className="eyebrow">{packLabel(t, c.pack)} / {c.id}</div><h2>{c.question.text}</h2><div className="case-tags"><span className="tag">{t("explore.cases.choiceCount", { n: fmt.number(c.question.labels.length) })}</span><span className="tag">{c.label_status === "teacher" ? t("explore.cases.labelSources.teacher") : c.label_status === "formal" ? t("explore.cases.labelSources.formal") : t("explore.cases.labelSources.dataset")}</span></div>
      <div className="evidence-block"><CaseState text={c.state}/></div>
      {c.question.rubric && <details className="explain"><summary>{t("explore.cases.decisionRules")}</summary><p>{c.question.rubric}</p></details>}
      {c.question.labels.length <= 8 ? <div className="answer-options">{c.question.labels.map(l => <span key={l}>{l}</span>)}</div> : <details className="explain"><summary>{t("explore.cases.showAllAnswers", { n: fmt.number(c.question.labels.length) })}</summary><div className="answer-options">{c.question.labels.map(l => <span key={l}>{l}</span>)}</div></details>}
      <button className="button secondary" onClick={() => setReveal(!reveal)}>{reveal ? t("explore.cases.hideAnswers") : t("explore.cases.revealAnswers")}</button>
      {reveal && <div className="answer-reveal"><div className="reference"><span>{t("explore.cases.savedReference")}</span><strong>{c.gold}</strong>{!!c.acceptable?.length && <small>{t("explore.cases.alsoAccepted", { answers: c.acceptable.join(", ") })}</small>}</div><h3>{t("explore.cases.modelDecisions")}</h3><div className="decision-rows">{detail.predictions.map(p => <div key={p.model_id}><div className="decision-title"><strong>{result?.entrants.find(e => e.id === p.model_id)?.name || p.model_id}</strong><span className={[c.gold, ...(c.acceptable || [])].includes(p.selected || "") ? "accent" : "muted"}>{p.selected || t("explore.cases.noSelectedAnswer")}</span><small>{fmt.duration(p.request_ms)} · {p.status}</small></div>{p.error && <p className="small muted">{p.error}</p>}{p.probabilities && <details className="explain"><summary>{t("explore.cases.optionProbabilities", { source: p.probability_source })}</summary><div className="prob-bars">{Object.entries(p.probabilities).map(([name, v]) => <div key={name}><span>{name}</span><div><i style={{ width: `${Math.max(0, Math.min(1, v)) * 100}%` }}/></div><b>{fmt.percent(v, 2)}</b></div>)}</div></details>}</div>)}</div>
      {result?.judge_jobs.filter(j => j.data.item.case_id === c.id && j.data.grade).map(j => <details className="explain" key={j.job_id}><summary>{t("explore.cases.astraAudit", { verdict: t(`results.verdicts.${j.data.grade?.verdict}`, { defaultValue: j.data.grade?.verdict }) })}</summary><p>{j.data.grade?.rationale}</p></details>)}</div>}
    </> : <p role="status">{loading || chosen ? t("explore.cases.loadingQuestion") : t("explore.cases.noMatches")}</p>}</section>
  </div></>;
}

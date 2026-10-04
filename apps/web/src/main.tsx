import React, { useEffect, useMemo, useState, useCallback, useRef } from "react";

import { createRoot } from "react-dom/client";

import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  Command,
  Cpu,
  Database,
  ExternalLink,
  FlaskConical,
  Layers3,
  Pause,
  Play,
  RotateCcw,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Square,
  Terminal,
  Timer,
  TriangleAlert,
  X,
  Zap,
} from "lucide-react";

import type {
  Model,
  Ready,
  Run,
  Result,
  Metrics,
  ArenaEvent,
  LocaleInfo,
} from "./types";
import { initI18n, setLanguage, useTranslation, useFormat, bundledLocales } from "./i18n";
import { safeLocale } from "./format";
import { Trans } from "react-i18next";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { EnglishOnly } from "./EnglishOnly";
import { packLabel, familyLabel, errorText, runLanguage, unpreparedSlots } from "./labels";


import "./styles.css";
import { AppShell } from "../../shared/AppShell";

import { Operations, EpisodeReplay } from "./Operations";
import { Takeaways, ModelGuide, SourcesGuide, TaskBreakdown, ABCDResults } from "./Guide";
import { ABCDCases } from "./ABCDCases";
import { EvidenceExplorer, TaskAnalysis, type CaseJump } from "./Explore";
import { NavigationProvider, useNavigation, useViewState } from "./ViewHistory";

const terminal = [
  "complete",
  "failed",
  "cancelled",
  "partial",
  "judging_incomplete",
  "interrupted",
];

const stages = [
  "preflight",
  "loading",
  "warming",
  "evaluating",
  "performance",
  "episodes",
  "unloading",
  "judging",
  "verifying",
  "complete",
];

declare global {
  interface Window {
    __ARENA_REPORT__?: { run: Run; result: Result; readiness: Ready; language?: string };
  }
}

const offline = window.__ARENA_REPORT__;

let token = "";

async function api<T>(path: string, body?: unknown): Promise<T> {
  if (offline) {
    if (body !== undefined)
      throw Object.assign(
        new Error("This saved report is read-only. Launch Jev Arena to run models."),
        { code: "report_read_only" },
      );
    return (
      path === "/i18n"
        ? { language: offline.language ?? "en", locales: bundledLocales }
        : path === "/readiness"
        ? offline.readiness
        : path === "/runs"
          ? [offline.run]
          : path.endsWith("/results")
            ? offline.result
            : path.includes("/cases")
              ? { total: 0, cases: [], predictions: [] }
              : path.endsWith("/timeline")
                ? []
                : offline.run
    ) as T;
  }

  if (body !== undefined && !token)
    token = (await (await fetch("/api/session")).json()).token;

  const r = await fetch(
    "/api" + path,
    body === undefined
      ? undefined
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Arena-Token": token,
          },
          body: JSON.stringify(body),
        },
  );

  if (!r.ok) {
    const data = await r.json().catch(() => ({ detail: r.statusText }));
    throw Object.assign(
      new Error(
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail),
      ),
      { code: data.code, params: data.params },
    );
  }
  return r.json();
}

const label = (s: string) =>
  s.replaceAll("_", " ").replace(/^./, (x) => x.toUpperCase());

const answerScore = (e: Result["entrants"][number]) => e.matched?.selected_label_accuracy ?? null;
const typicalTime = (result: Result | null, id: string) => {
  const blocks = result?.performance?.[id]?.blocks.map(b=>b.p50_ms).sort((a,b)=>a-b) || [];
  return blocks.length ? blocks[Math.floor(blocks.length/2)] : result?.entrants.find(e=>e.id===id)?.metrics.p50_ms;
};
function App({ locales }: { locales: LocaleInfo[] }) {
  const { t, i18n } = useTranslation();
  const fmt = useFormat();
  const tRef = useRef(t);
  tRef.current = t;
  const statusLabel = (s: string) => (s ? t(`status.${s}`, { defaultValue: label(s) }) : "");
  const presetLabel = (p: string) =>
    ({ smoke: t("common.presets.smoke"), demo: t("common.presets.demo"), full: t("common.presets.full") })[p] ?? label(p);
  const { page, navigate: setPage, back, canGoBack, backLabel } = useNavigation();
  const [resultsAssessment, setResultsAssessment] = useViewState("resultsAssessment", "arena");
  const [caseDataset, setCaseDataset] = useViewState("caseDataset", "arena");
  const [rid, setRid] = useViewState<string | null>("runId", null);
  const openCases = (jump: CaseJump) => setPage("cases", { caseDataset: "arena",
    [`cases:${rid}:filters`]: { pack: jump.pack, family: jump.family, model: jump.model || "", search: jump.search || "", kind: "", outcome: "", offset: 0 },
    [`cases:${rid}:search`]: jump.search || "", [`cases:${rid}:chosen`]: "" });
  const openAnalysis = (jump: CaseJump) => setPage("results", { resultsAssessment: "arena",
    [`analysis:${rid}:group`]: `${jump.pack}::${jump.family}`, [`analysis:${rid}:model`]: jump.model || "" });
  const openAbcdCases = () => setPage("cases", { caseDataset: "abcd" });
  const
    [ready, setReady] = useState<Ready | null>(null),
    [runs, setRuns] = useState<Run[]>([]),
    [result, setResult] = useState<Result | null>(null),
    [events, setEvents] = useState<ArenaEvent[]>([]);
  const showingAbcd = page === "abcd" || (page === "cases" && caseDataset === "abcd") || (page === "results" && resultsAssessment === "abcd");

  const [selected, setSelected] = useState<string[]>([
      "jev",
      "plumb",
      "decider",
      "winnow",
      "semif",
      "clm",
      "nimble",
      "laya",
    ]),
    [preset, setPreset] = useState("full"),
    [judge, setJudge] = useState(true),
    [drawer, setDrawer] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [focus, setFocus] = useViewState<string | null>("focusedModel", null),
    [present, setPresent] = useState(false);

  async function changeLanguage(code: string) {
    try {
      if (!offline) await api("/i18n", { language: code });
      await setLanguage(code);
    } catch (e) {
      setError(errorText(t, e));
    }
  }

  const refresh = useCallback(async () => {
    try {
      const [a, b] = await Promise.all([
        api<Ready>("/readiness"),
        api<Run[]>("/runs"),
      ]);
      setReady(a);
      setRuns(b);
      setRid(
        (old) =>
          old ||
          b.find((r) => !terminal.includes(r.status))?.id ||
          b.find(
            (r) => r.status === "complete" && r.request.model_ids.length > 1,
          )?.id ||
          b.find((r) => r.status === "complete")?.id ||
          b[0]?.id ||
          null,
      );
    } catch (e) {
      setError(errorText(tRef.current, e));
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 12000);
    return () => clearInterval(t);
  }, [refresh]);

  const loadResult = useCallback(async () => {
    if (rid) {
      try {
        setResult(await api<Result>(`/runs/${rid}/results`));
      } catch (e) {
        setError(errorText(tRef.current, e));
      }
    }
  }, [rid]);

  const selectedRunStatus = runs.find(run => run.id === rid)?.status;
  const isLiveRun = !!selectedRunStatus && !terminal.includes(selectedRunStatus);
  useEffect(() => {
    setResult(null);
    setEvents([]);
    loadResult();
    // Completed evidence has no live events to follow. Replaying its entire
    // history repeatedly fetched the large result file while browsing cases.
    if (!rid || offline || !isLiveRun) return;
    let update: ReturnType<typeof setTimeout> | null = null;
    const es = new EventSource(`/api/runs/${rid}/events`);
    es.addEventListener("arena", (e) => {
      const item = JSON.parse((e as MessageEvent).data);
      setEvents((prev) => [...prev.slice(-500), item]);
      if (!update)
        update = setTimeout(() => {
          loadResult();
          refresh();
          update = null;
        }, 1000);
    });
    es.addEventListener("done", () => {
      es.close();
      loadResult();
      refresh();
    });
    return () => {
      es.close();
      if (update) clearTimeout(update);
    };
  }, [rid, isLiveRun, loadResult, refresh]);

  useEffect(() => {
    if (!drawer) return;
    const before = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector(".drawer") as HTMLElement;
    const focusable = () =>
      Array.from(
        dialog.querySelectorAll<HTMLElement>(
          "button:not([disabled]),input,select,a[href]",
        ),
      );
    focusable()[0]?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawer(false);
      if (e.key === "Tab") {
        const all = focusable(),
          first = all[0],
          last = all.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", key);
      document.body.style.overflow = previous;
      before?.focus();
    };
  }, [drawer]);

  const current = runs.find((r) => r.id === rid),
    active = !!current && !terminal.includes(current.status),
    models = ready?.models || [],
    blocked = models.filter((m) => selected.includes(m.id) && !m.ready),
    metricRows = result?.entrants || [];

  // Case counts come from the inventory of the active test-data language; the constants are the English sizes.
  const presetCount = (p: string) =>
    ready?.suites.presets.find((x) => x.id === p)?.count ?? (p === "full" ? 7671 : p === "demo" ? 120 : 36);
  const dataLanguage = ready?.suites.language || "en";
  const dataLine = (p: string) =>
    ready && (
      <p className="data-language small muted">
        {t("setup.dataLanguage", { language: fmt.languageName(dataLanguage), count: presetCount(p), n: fmt.number(presetCount(p)) })}
        {unpreparedSlots(ready.suites.slots).length > 0 && !offline && (
          <>
            {" · "}
            <button className="text-button" onClick={() => { setDrawer(false); setPage("setup"); }}>
              {t("setup.prepareDataFirst", { language: fmt.languageName(dataLanguage) })}
            </button>
          </>
        )}
      </p>
    );
  const currentLanguage = runLanguage(current);

  const displayPreset =
    active || offline ? current?.request.preset || preset : preset;

  const planned = result
    ? result.case_count * result.entrants.length
    : presetCount(preset) * selected.length;

  const completed = metricRows.reduce((sum, e) => sum + e.metrics.completed, 0),
    best = metricRows
      .filter((e) => answerScore(e) != null)
      .sort((a, b) => answerScore(b)! - answerScore(a)!)[0];

  const runStages = stages.filter(
    (s) =>
      !(
        (s === "performance" && current?.request.preset !== "full") ||
        (s === "episodes" &&
          !["full", "demo"].includes(current?.request.preset || "")) ||
        (s === "judging" && !current?.request.judge)
      ),
  );

  const stage =
    (events.filter((e) => e.kind === "stage").at(-1)?.data.stage as string) ||
    current?.status ||
    "ready";

  const liveModel = events.filter((e) => e.kind === "model").at(-1)?.data
    .model_id as string | undefined;

  async function start() {
    setBusy(true);
    setError("");
    try {
      const r = await api<{ id: string }>("/runs", {
        preset,
        model_ids: selected,
        judge,
        paid_cap_usd: 5,
        seed: 5090,
        idempotency_key: crypto.randomUUID(),
      });
      setRid(r.id);
      setPage("arena");
      setDrawer(false);
      await refresh();
    } catch (e) {
      setError(errorText(t, e));
      setDrawer(true);
    } finally {
      setBusy(false);
    }
  }

  async function mutate(path: string) {
    try {
      await api(path, {});
      await refresh();
    } catch (e) {
      setError(errorText(t, e));
    }
  }

  function toggle(mid: string) {
    setSelected((s) =>
      s.includes(mid) ? s.filter((x) => x !== mid) : [...s, mid],
    );
  }

  const heading: Record<string, [string, string]> = {
    models: [t("overview.heading.models"), t("overview.lead.models")],
    takeaways: [t("overview.heading.takeaways"), t("overview.lead.takeaways")],
    sources: [t("overview.heading.sources"), t("overview.lead.sources")],
    abcd: [t("overview.heading.abcd"), t("overview.lead.abcd")],
    run: [t("overview.heading.run"), t("overview.lead.run")],
    chart: [t("overview.heading.chart"), t("overview.lead.chart")],
    arena: [t("overview.heading.arena"), t("overview.lead.arena")],
    results: [t("overview.heading.results"), t("overview.lead.results")],
    cases: [t("overview.heading.cases"), t("overview.lead.cases")],
    replay: [t("overview.heading.replay"), t("overview.lead.replay")],
  };
  const [pageTitle, pageLead] = heading[page] ?? [t("overview.heading.setup"), t("overview.lead.setup")];

  return (
    <>
      <AppShell
        appName="Jev Arena"
        description={t("shell.description")}
        labels={{
          skipToContent: t("shell.skipToContent"),
          expandNavigation: t("shell.expandNavigation"),
          collapseNavigation: t("shell.collapseNavigation"),
          presenter: t("shell.presenter"),
          exitPresenter: t("shell.exitPresenter"),
          exitPresenterTitle: t("shell.exitPresenterTitle"),
          presenterTitle: t("shell.presenterTitle"),
          workspace: t("shell.workspace"),
          localWorkspace: t("shell.localWorkspace"),
          homeLabel: t("shell.homeLabel", { appName: "Jev Arena" }),
          workspaceLabel: t("shell.workspaceLabel", { appName: "Jev Arena" }),
          navigationLabel: t("shell.navigationLabel", { appName: "Jev Arena" }),
        }}
        headerExtra={<LanguageSwitcher locales={locales} language={i18n.language} onChange={changeLanguage} />}
        navigation={[
          { id: "arena", label: t("nav.arena"), icon: Activity },
          { id: "takeaways", label: t("nav.takeaways"), icon: Sparkles },
          { id: "models", label: t("nav.models"), icon: Cpu },
          { id: "abcd", label: t("nav.abcd"), icon: Database },
          { id: "sources", label: t("nav.sources"), icon: ShieldCheck },
          { id: "results", label: t("nav.results"), icon: Layers3 },
          { id: "cases", label: t("nav.cases"), icon: FlaskConical },
          { id: "replay", label: t("nav.replay"), icon: Play },
          { id: "run", label: t("nav.run"), icon: Play },
          { id: "setup", label: t("nav.setup"), icon: Settings2 },
        ]}
        activePage={page}
        onNavigate={setPage}
        presenter={present}
        onPresenterChange={setPresent}
        status={offline ? t("overview.savedReport") : ready?.hardware.gpu?.name.replace("NVIDIA GeForce ", "") || t("shell.localWorkspace")}
        sidebarFooter={<><p>{t("overview.sidebarTagline")}</p><button className="text-button" onClick={()=>setPage("sources")}>{t("overview.allSources")}</button></>}
        footerNote={showingAbcd ? t("overview.footerAbcd") : result ? `${result.run_id} · ${statusLabel(current?.status || "")}` : t("overview.footerNone")}
        className={`page-${page}`}
      >
          {offline && (
            <div className="setup-progress">
              <ShieldCheck size={17} /> {t("overview.offlineBanner")}
            </div>
          )}

          {error && (
            <div className="alert" role="alert">
              <TriangleAlert size={17} />
              <span>{error}</span>
              <button onClick={() => setError("")} aria-label={t("common.dismissError")}>
                <X size={16} />
              </button>
            </div>
          )}

          {canGoBack ? <button className="text-button page-back" onClick={back}>{t("common.backTo", { target: backLabel })}</button> : page === "cases" ? <button className="text-button page-back" onClick={()=>setPage("results")}>{t("common.backTo", { target: t("nav.results") })}</button> : null}
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span className="status-dot" />
                {active
                  ? t("overview.eyebrowInProgress")
                  : completed
                    ? t("overview.eyebrowMeasured")
                    : t("overview.eyebrowLab")}
                {current && currentLanguage !== "en" && !showingAbcd && (
                  <span className="tag language-badge" title={t("overview.runLanguage", { language: fmt.languageName(currentLanguage) })}>
                    {currentLanguage.toUpperCase()}
                  </span>
                )}
              </div>
              <h1>{pageTitle}</h1>
              <p>{pageLead}</p>
            </div>
            <div className="heading-actions">
              {runs.length > 0 && !showingAbcd && (
                <select
                  aria-label={t("overview.selectSavedRun")}
                  value={rid || ""}
                  onChange={(e) => setRid(e.target.value)}
                >
                  {runs.map((r) => {
                    const option = t("overview.runOption", {
                      date: fmt.shortDate(r.created),
                      preset: presetLabel(r.request.preset).toLocaleLowerCase(safeLocale(i18n.language)),
                      count: r.request.model_ids.length,
                      id: r.id.slice(-6),
                      status: statusLabel(r.status),
                    });
                    const lang = runLanguage(r);
                    return (
                      <option value={r.id} key={r.id}>
                        {lang === "en" ? option : t("overview.runOptionLanguage", { option, code: lang.toUpperCase() })}
                      </option>
                    );
                  })}
                </select>
              )}
              {rid && !offline && !showingAbcd && (
                <a
                  className="button secondary compact"
                  href={`/api/runs/${rid}/export`}
                >
                  <ArrowDownToLine size={16} /> {t("overview.export")}
                </a>
              )}
              {(page === "run" || page === "setup") && (<button
                className="button secondary compact"
                disabled={!!offline}
                onClick={() => setDrawer(true)}
              >
                <SlidersHorizontal size={16} /> {t("overview.newTestSettings")}
              </button>)}

            </div>
          </div>

          {result?.run_id === "20260927-205440-6350b9" && (page === "arena" || (page === "results" && !showingAbcd)) && (
            <details className="explain"><summary>{t("overview.headlineExplain.summary")}</summary>
              <p>{t("overview.headlineExplain.scoring")}</p>
              <p>{t("overview.headlineExplain.exclusions")}</p>
              <p>{t("overview.headlineExplain.winnow")}</p>
            </details>
          )}
          {page === "models" && <ModelGuide selected={focus} onSelect={setFocus}/>}
          {page === "takeaways" && <><Takeaways onModels={()=>setPage("models")} onAbcd={()=>setPage("abcd")} onAnalysis={openAnalysis}/><TaskBreakdown/><p className="small muted">{t("overview.takeawaysNote")}</p></>}
          {page === "sources" && <SourcesGuide/>}
          {page === "abcd" && <><button className="text-button" onClick={openAbcdCases}>{t("overview.inspectAbcdCases")}</button><ABCDResults/></>}
          {page === "chart" && <section className="frontier-panel chart-large"><button className="text-button" onClick={()=>setPage("arena")}>{t("overview.backToOverview")}</button><Frontier rows={metricRows} result={result} focus={focus} onFocus={setFocus}/><p className="small muted">{t("overview.chartNote")}</p></section>}

          {page === "arena" && (
            <>
              <div className="workspace-bar">
                <div className="workspace-tabs">
                  <button className="selected">{t("nav.arena")}</button>
                  <button onClick={() => setPage("results")}>
                    {t("overview.tabQuality")}
                  </button>
                  <button onClick={() => setPage("replay")}>
                    {t("overview.tabReplay")} <ArrowUpRight size={12} />
                  </button>
                </div>
                <span className="scope-label">
                  {result
                    ? t("overview.scope", {
                        preset: presetLabel(result.preset).toLocaleUpperCase(safeLocale(i18n.language)),
                        version: String(current?.manifest.version || "arena-v1").replace("arena-", "").toUpperCase(),
                        count: result.case_count,
                        n: fmt.number(result.case_count),
                      })
                    : t("overview.scopeDefault", { n: fmt.number(presetCount("full")) })}
                </span>
              </div>

              <div className="arena-layout">
                <div className="main-column">
                  <div className="metrics-strip">
                    <Metric
                      name={t("overview.metric.decisions")}
                      value={fmt.number(completed)}
                      detail={t("overview.metric.decisionsDetail", { n: fmt.number(planned) })}
                      large
                    />
                    <Metric
                      name={t("overview.metric.bestAccuracy")}
                      value={best ? fmt.percent(answerScore(best),2) : "—"}
                      detail={
                        best
                          ? t("overview.metric.bestAccuracyDetail", { name: best.name })
                          : t("overview.metric.awaitingResults")
                      }
                    />
                    <Metric
                      name={t("overview.metric.models")}
                      value={String(
                        result?.entrants.length || selected.length,
                      ).padStart(2, "0")}
                      detail={
                        result
                          ? t("overview.metric.modelsSameManifest")
                          : t("overview.metric.modelsRoster")
                      }
                    />
                    <Metric
                      name={t("overview.metric.mainScore")}
                      value={t("overview.metric.answerKey")}
                      detail={
                        (current ? current.request.judge : judge)
                          ? t("overview.metric.judgeSpotChecks")
                          : t("overview.metric.scoredAgainstAnswers")
                      }
                      text
                    />
                  </div>

                  <section className="frontier-panel">
                    <div className="section-title">
                      <div>
                        <h2>{t("overview.chartTitle")}</h2>
                        <p>{t("overview.chartLead")}</p>
                      </div>
                      <span className={`tag ${completed ? "measured" : ""}`}>
                        {completed
                          ? active
                            ? t("overview.tagLive")
                            : t("overview.tagMeasured")
                          : t("overview.tagAwaiting")}
                      </span>
                    </div>
                    <Frontier
                      result={result}
                      rows={metricRows}
                      focus={focus}
                      onFocus={setFocus}
                    />
                    <div className="chart-foot">
                      <span>
                        <span className="tiny-square" /> {t("overview.selectedEntrant")}
                      </span>
                      <span>{t("overview.timingNote")}</span>
                      <button onClick={() => setPage("chart")}>
                        {t("overview.enlargeChart")} <ArrowRight size={13} />
                      </button>
                    </div>
                  </section>

                  <section className="model-panel">
                    <div className="section-title">
                      <div>
                        <h2>
                          {t("overview.entrantComparison")}{" "}
                          <span className="count">
                            {result?.entrants.length || selected.length}
                          </span>
                        </h2>
                      </div>
                      <button
                        className="text-button"
                        disabled={!!offline}
                        onClick={() => setDrawer(true)}
                      >
                        {t("overview.manageEntrants")} <SlidersHorizontal size={13} />
                      </button>
                    </div>
                    <p className="small muted score-note">{t("overview.scoreNote", { n: fmt.number(metricRows[0]?.matched?.verified_count) })}</p>
                    <div className="table-scroll"><table><thead><tr><th>{t("overview.table.model")}</th><th>{t("overview.table.answerAccuracy")}</th><th>{t("overview.table.typicalResponse")}</th><th>{t("overview.table.outputsPassing")}</th></tr></thead><tbody>
                    {[...metricRows].sort((a,b)=>(answerScore(b)??-1)-(answerScore(a)??-1)).map(e=><tr key={e.id}>
                    <td><button className="model-link" onClick={()=>{setFocus(e.id);setPage("models")}}>{e.name} <ChevronRight size={14}/></button></td>
                    <td className="tabular bright">{fmt.percent(answerScore(e),2)}<small className="table-note">{t("overview.table.answersCorrect", { correct: fmt.number(e.matched?.selected_label_correct), total: fmt.number(e.matched?.verified_count) })}</small></td>
                    <td className="tabular">{fmt.duration(typicalTime(result,e.id))}</td>
                    <td>{fmt.percent(e.metrics.coverage, 2)}<small className="table-note">{t("overview.table.validPlanned", { valid: fmt.number(e.metrics.valid), planned: fmt.number(e.metrics.planned) })}</small></td>
                    </tr>)}</tbody></table></div>

                  </section>
                </div>


              </div>
              {result?.run_id === "20260927-205440-6350b9" && <Takeaways onModels={()=>setPage("models")} onAbcd={()=>setPage("abcd")} onAnalysis={openAnalysis}/>}

              <div className="method-strip">
                <div>
                  <ShieldCheck size={19} />
                  <span>
                    {t("overview.method.evidenceTitle")}
                    <strong>{t("overview.method.evidenceDetail")}</strong>
                  </span>
                </div>
                <div>
                  <Layers3 size={19} />
                  <span>
                    {t("overview.method.sequentialTitle")}
                    <strong>{t("overview.method.sequentialDetail")}</strong>
                  </span>
                </div>
                <button className="text-button" onClick={()=>setPage("sources")}>{t("overview.allSourcesLink")} <ExternalLink size={13}/></button>
              </div>
            </>
          )}

          {page === "results" && (
            <><div className="quick-types assessment-tabs" role="group" aria-label={t("overview.resultsAssessment")}>
              <button aria-pressed={resultsAssessment === "arena"} className={resultsAssessment === "arena" ? "selected" : ""} onClick={()=>setResultsAssessment("arena")}>{t("overview.assessmentArenaRun")}</button>
              <button aria-pressed={resultsAssessment === "abcd"} className={resultsAssessment === "abcd" ? "selected" : ""} onClick={()=>setResultsAssessment("abcd")}>{t("overview.assessmentAbcd")}</button>
            </div>{resultsAssessment === "abcd" ? <><button className="text-button" onClick={openAbcdCases}>{t("overview.inspectAbcdCases")}</button><ABCDResults/></> : <>{result && <TaskAnalysis key={result.run_id} result={result} onCases={openCases}/>}<details className="whole-run-details"><summary>{t("overview.wholeRunDiagnostics")}</summary><Results result={result} focus={focus} onFocus={setFocus} onProfile={(id)=>{setFocus(id);setPage("models")}} /></details></>}</>
          )}

          {page === "cases" && (
            <><label className="case-dataset">{t("overview.assessment")}<select value={caseDataset} onChange={e=>setCaseDataset(e.target.value)}><option value="arena">{t("overview.assessmentArenaBenchmark")}</option><option value="abcd">{t("overview.assessmentAbcd")}</option></select></label>{caseDataset==="abcd"?<ABCDCases offline={!!offline}/>:<EvidenceExplorer rid={rid} result={result} />}</>
          )}

          {page === "replay" &&
            (result ? (
              <EpisodeReplay result={result} />
            ) : (
              <Replay rid={rid} result={result} />
            ))}

          {page === "run" && (<aside className="run-panel">
                  <div className="run-panel-top">
                    <span className="eyebrow">{t("overview.run.control")}</span>
                    <span className="run-number">
                      {current
                        ? "#" + current.id.slice(-6).toUpperCase()
                        : t("overview.run.newRunNumber")}
                    </span>
                  </div>
                  <div className="run-orbit">
                    <svg viewBox="0 0 180 180">
                      <circle cx="90" cy="90" r="77" className="orbit-bg" />
                      <circle
                        cx="90"
                        cy="90"
                        r="77"
                        className="orbit-progress"
                        strokeDasharray={`${Math.min(1, completed / Math.max(1, planned)) * 484} 484`}
                      />
                      {Array.from({ length: 40 }, (_, i) => {
                        const a = (i / 40) * Math.PI * 2;
                        return (
                          <line
                            key={i}
                            x1={90 + 66 * Math.cos(a)}
                            y1={90 + 66 * Math.sin(a)}
                            x2={90 + 69 * Math.cos(a)}
                            y2={90 + 69 * Math.sin(a)}
                          />
                        );
                      })}
                    </svg>
                    <div>
                      {active ? (
                        <Activity size={31} />
                      ) : current?.status === "complete" ? (
                        <Check size={32} />
                      ) : (
                        <Command size={30} />
                      )}
                      <strong>
                        {active
                          ? fmt.percent(completed / Math.max(planned, 1), 0)
                          : current?.status === "complete"
                            ? statusLabel("complete")
                            : t("overview.run.newTest")}
                      </strong>
                      <span>{active ? statusLabel(stage) : t("overview.run.savedRunStatus")}</span>
                    </div>
                  </div>
                  <p className="run-description">{t("overview.run.description")}</p>

                  {active ? (
                    <button
                      className="button stop"
                      onClick={() => mutate(`/runs/${rid}/cancel`)}
                    >
                      <Square size={15} /> {t("overview.run.stop")}
                    </button>
                  ) : (
                    <button
                      className="button primary impress"
                      onClick={() => setDrawer(true)}
                      disabled={!!offline || busy || !selected.length}
                    >
                      {busy ? (
                        <Activity className="spin" size={18} />
                      ) : (
                        <Zap size={18} />
                      )}{" "}
                      {t("overview.run.configure")} <ArrowRight size={18} />
                    </button>
                  )}

                  <button
                    className="preset-line"
                    disabled={!!offline || active}
                    onClick={() => setDrawer(true)}
                  >
                    <span>
                      {!active && !offline
                        ? t("overview.run.nextSuite", { preset: presetLabel(displayPreset) })
                        : t("overview.run.suite", { preset: presetLabel(displayPreset) })}
                    </span>
                    <span>
                      {t("overview.run.cases", { count: presetCount(displayPreset), n: fmt.number(presetCount(displayPreset)) })}{" "}
                      <ChevronDown size={12} />
                    </span>
                  </button>
                  {!active && dataLine(displayPreset)}

                  {blocked.length > 0 && !active && (
                    <button
                      className="setup-hint"
                      onClick={() => {
                        setPage("setup");
                        setDrawer(false);
                      }}
                    >
                      <TriangleAlert size={14} />
                      <span>{t("overview.run.entrantsNeedSetup", { count: blocked.length })}</span>
                      <ArrowUpRight size={13} />
                    </button>
                  )}

                  <div className="stage-list">
                    {runStages.map((s, i) => {
                      const at = runStages.indexOf(stage),
                        done = current?.status === "complete" || at > i;
                      return (
                        <div
                          key={s}
                          className={`${done ? "done" : ""} ${stage === s ? "current" : ""}`}
                        >
                          <span>
                            {done ? (
                              <Check size={11} />
                            ) : (
                              String(i + 1).padStart(2, "0")
                            )}
                          </span>
                          <b>{statusLabel(s)}</b>
                          {stage === s && active && (
                            <span className="stage-live" />
                          )}
                        </div>
                      );
                    })}
                  </div>

                  <div className="hardware-mini">
                    <Cpu size={17} />
                    <div>
                      <strong>
                        {ready?.hardware.gpu?.name.replace(
                          "NVIDIA GeForce ",
                          "",
                        ) || t("overview.run.gpuNotDetected")}
                      </strong>
                      <span>
                        {t("overview.run.gpuMemory", {
                          gb: fmt.number((ready?.hardware.gpu?.memory_total_mb || 0) / 1024, 1),
                          temp: fmt.number(ready?.hardware.gpu?.temperature_c),
                        })}
                      </span>
                    </div>
                    <span className="status-dot" />
                  </div>
                  {liveModel && active && (
                    <div className="currently">
                      <Trans
                        i18nKey="overview.run.nowRunning"
                        values={{ name: models.find((m) => m.id === liveModel)?.name }}
                        components={{ b: <strong /> }}
                      />
                    </div>
                  )}

                  {current?.error && (
                    <div className="run-error">
                      {current.error}
                      {!active && current.status !== "complete" && (
                        <button
                          className="text-button"
                          onClick={() => mutate(`/runs/${rid}/resume`)}
                        >
                          {t("overview.run.resume")} <RotateCcw size={13} />
                        </button>
                      )}
                    </div>
                  )}
                </aside>)}

          {page === "setup" && (
            <Setup
              ready={ready}
              selected={selected}
              toggle={toggle}
              onRefresh={refresh}
              onError={setError}
              onLocal={() => {
                setSelected(
                  models
                    .filter((m) => m.ready && !m.hosted && m.id !== "uniform")
                    .map((m) => m.id),
                );
                setPreset("smoke");
                setDrawer(true);
              }}
            />
          )}

      </AppShell>

      {drawer && (
        <div className="drawer-backdrop" onClick={() => setDrawer(false)}>
          <section
            className="drawer"
            role="dialog"
            aria-modal="true"
            aria-label={t("overview.drawer.label")}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="drawer-title">
              <div>
                <span className="eyebrow">{t("overview.drawer.eyebrow")}</span>
                <h2>{t("overview.drawer.title")}</h2>
              </div>
              <button
                className="icon-btn"
                onClick={() => setDrawer(false)}
                aria-label={t("overview.drawer.close")}
              >
                <X />
              </button>
            </div>
            <label className="field-label">{t("overview.drawer.suite")}</label>
            <div className="preset-options">
              {[
                ["smoke", t("overview.drawer.smokeDescription")],
                ["demo", t("overview.drawer.demoDescription")],
                ["full", t("overview.drawer.fullDescription")],
              ].map(([p, desc]) => (
                <button
                  className={preset === p ? "selected" : ""}
                  key={p}
                  onClick={() => setPreset(p)}
                >
                  <span>
                    {presetLabel(p)} <b>{fmt.number(presetCount(p))}</b>
                  </span>
                  <small>{desc}</small>
                </button>
              ))}
            </div>
            {dataLine(preset)}
            <div className="field-row">
              <label className="field-label">
                {t("overview.drawer.entrants")} <span>{t("overview.drawer.selectedCount", { count: selected.length })}</span>
              </label>
              <button
                className="text-button"
                onClick={() =>
                  setSelected(
                    models
                      .filter((m) => m.ready && m.id !== "uniform")
                      .map((m) => m.id),
                  )
                }
              >
                {t("overview.drawer.selectReady")}
              </button>
            </div>
            <div className="entrant-select">
              {models.map((m) => (
                <label key={m.id}>
                  <input
                    type="checkbox"
                    checked={selected.includes(m.id)}
                    onChange={() => toggle(m.id)}
                  />
                  <span>
                    <strong>{m.name}</strong>
                    <small>
                      {m.hosted ? t("overview.drawer.hosted") : t("overview.drawer.local", { size: m.size })}
                      {m.diagnostic && <> · {t("overview.drawer.control")}</>}
                    </small>
                  </span>
                  <span className={m.ready ? "accent" : "muted"}>
                    {m.ready ? t("overview.drawer.ready") : t("overview.drawer.needsSetup")}
                  </span>
                </label>
              ))}
            </div>
            <label className="judge-toggle">
              <input
                type="checkbox"
                checked={judge}
                onChange={(e) => setJudge(e.target.checked)}
              />
              <span>
                <strong>{t("overview.drawer.judgeTitle")}</strong>
                <small>{t("overview.drawer.judgeDetail")}</small>
              </span>
            </label>
            <div className="config-note">
              <ShieldCheck size={16} />
              <span>{t("overview.drawer.costNote")}</span>
            </div>
            <button
              className="button primary"
              disabled={busy || !selected.length || active}
              onClick={start}
            >
              <Zap size={17} /> {t("overview.drawer.start", { preset: presetLabel(preset) })}{" "}
              <ArrowRight size={17} />
            </button>
            {blocked.length > 0 && (
              <p className="muted small">
                {t("overview.drawer.entrantsNeedPreparation", { count: blocked.length })}
              </p>
            )}
          </section>
        </div>
      )}
    </>
  );
}

function Metric({
  name,
  value,
  detail,
  large = false,
  text = false,
}: {
  name: string;
  value: string;
  detail: string;
  large?: boolean;
  text?: boolean;
}) {
  return (
    <div
      className={`metric ${large ? "major" : ""} ${text ? "text-metric" : ""}`}
    >
      <span>{name}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function Frontier({
  result,
  rows,
  focus,
  onFocus,
}: {
  result: Result | null;
  rows: Result["entrants"];
  focus: string | null;
  onFocus: (id: string | null) => void;
}) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const chartRows = rows.map(e=>({...e, metrics:{...e.metrics, accuracy:answerScore(e), p50_ms:typicalTime(result,e.id)??null}}));
  const measured = chartRows.filter(
      (e) => e.metrics.p50_ms != null && e.metrics.accuracy != null,
    ),
    max = Math.max(100, ...measured.map((e) => e.metrics.p50_ms! * 1.5));

  const x = (v: number) =>
      72 + (Math.log10(Math.max(1, v)) / Math.log10(max)) * 740,
    y = (v: number) => 375 - v * 302;

  return (
    <div className="frontier-chart">
      <svg
        viewBox="0 0 880 430"
        role="img"
        aria-label={
          measured.length
            ? t("overview.frontier.label")
            : t("overview.frontier.emptyLabel")
        }
      >
        <defs>
          <pattern
            id="dots"
            width="18"
            height="18"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="1" cy="1" r=".65" fill="var(--line)" />
          </pattern>
        </defs>
        <rect x="72" y="38" width="740" height="338" fill="url(#dots)" />
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line x1="72" x2="812" y1={y(v)} y2={y(v)} className="grid-line" />
            <text x="53" y={y(v) + 4} textAnchor="end">
              {fmt.percent(v, 0)}
            </text>
          </g>
        ))}
        {[1, 10, 100, 1000, 10000]
          .filter((v) => v <= max)
          .map((v) => (
            <g key={v}>
              <line
                x1={x(v)}
                x2={x(v)}
                y1="38"
                y2="375"
                className="grid-line vertical-line"
              />
              <text x={x(v)} y="397" textAnchor="middle">
                {fmt.duration(v)}
              </text>
            </g>
          ))}
        <text x="73" y="22" className="axis-label">
          {t("overview.frontier.yAxis")}
        </text>
        <text x="812" y="420" textAnchor="end" className="axis-label">
          {t("overview.frontier.xAxis")}
        </text>
        <text x="91" y="62" className="ideal-label">
          {t("overview.frontier.ideal")}
        </text>
        {measured.map((e, i) => {
          const chosen = focus === e.id || (!focus && i === 0);
          return (
            <g
              key={e.id}
              className={`chart-point ${chosen ? "selected" : ""}`}
              tabIndex={0}
              role="button"
              aria-label={`${e.name}: ${fmt.percent(e.metrics.accuracy)}, ${fmt.duration(e.metrics.p50_ms)}`}
              onMouseEnter={() => onFocus(e.id)}
              onFocus={() => onFocus(e.id)}
              onClick={() => onFocus(e.id)}
              onKeyDown={(ev) => {
                if (ev.key === "Enter") onFocus(e.id);
              }}
            >
              <circle
                className="point-halo"
                cx={x(e.metrics.p50_ms!)}
                cy={y(e.metrics.accuracy!)}
                r={chosen ? 15 : 10}
              />
              <circle
                cx={x(e.metrics.p50_ms!)}
                cy={y(e.metrics.accuracy!)}
                r={chosen ? 5.5 : 4}
              />
              {chosen && (
                <text
                  x={Math.min(740, x(e.metrics.p50_ms!) + 13)}
                  y={y(e.metrics.accuracy!) - 12}
                >
                  {e.name}
                </text>
              )}
            </g>
          );
        })}
        {!measured.length && (
          <g className="chart-empty">
            <path d="M408 142h20l9-19 13 42 12-30h25" />
            <text x="447" y="199" textAnchor="middle">
              {t("overview.frontier.emptyTitle")}
            </text>
            <text x="447" y="218" textAnchor="middle" className="sub">
              {t("overview.frontier.emptyDetail")}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}

function Results({
  onProfile,
  result,
  focus,
  onFocus,
}: {
  result: Result | null;
  onProfile: (id: string) => void;
  focus: string | null;
  onFocus: (s: string) => void;
}) {
  const { t } = useTranslation();
  const fmt = useFormat();

  if (!result || !result.entrants.length)
    return (
      <Empty
        icon={Layers3}
        title={t("results.emptyTitle")}
        detail={t("results.emptyDetail")}
      />
    );

  const e = result.entrants.find((e) => e.id === focus) || result.entrants[0],
    m = e.metrics;

  const reviews = result.judge_jobs.filter(
    (j) => j.status === "complete" && j.data.models.includes(e.id),
  );
  const accepted = reviews.filter((j) => ["correct", "acceptable"].includes(j.data.grade?.verdict || "")).length;
  // Keeps the "N/A" fallback for missing values (fmt.fixed would render "—").
  const fixedOrNull = (v: number | null | undefined, d: number) => (v == null ? null : fmt.fixed(v, d));
  const verdictLabel = (v: string) => (v ? t(`results.verdicts.${v}`, { defaultValue: label(v) }) : "");

  return (
    <>
      <div className="results-select">
        {result.entrants.map((r) => (
          <button
            className={r.id === e.id ? "selected" : ""}
            key={r.id}
            onClick={() => onFocus(r.id)}
          >
            {r.name}
            <span>{fmt.percent(answerScore(r), 2)}</span>
          </button>
        ))}
      </div>
      <div className="results-context">
        <h2>{e.name}</h2><button className="text-button" onClick={()=>onProfile(e.id)}>{t("results.aboutModel")}</button>
        <span>
          {t("results.sharedCorrect", {
            correct: fmt.number(e.matched.selected_label_correct),
            total: fmt.number(e.matched.verified_count),
          })}
        </span>
      </div>
      <div className="metrics-strip result-metrics">
        <Metric
          name={t("results.answerAccuracy")}
          value={fmt.percent(answerScore(e), 2)}
          detail={t("results.answerAccuracyDetail")}
          large
        />
        <Metric
          name={t("results.outputsPassing")}
          value={fmt.percent(m.coverage)}
          detail={t("results.outputsPassingDetail", { valid: fmt.number(m.valid), planned: fmt.number(m.planned) })}
        />
        <Metric
          name={t("results.slowerRequests")}
          value={fmt.duration(m.p95_ms)}
          detail={t("results.slowerRequestsDetail")}
        />
        <Metric
          name={t("results.confidenceMismatch")}
          value={fmt.percent(m.ece)}
          detail={t("results.confidenceMismatchDetail", { n: fmt.number(m.probability_count) })}
        />
      </div>
      <div className="results-grid">
        <section className="analysis-panel">
          <div className="section-title">
            <div>
              <h2>{t("results.calibration.title")}</h2>
              <p>{t("results.calibration.intro")}</p>
            </div>
            <span className="tag">{t("results.calibration.tag")}</span>
          </div>
          {!m.probability_count && <p className="small muted">{t("results.calibration.noProbabilities")}</p>}
          <svg
            viewBox="0 0 580 285"
            className="reliability-chart"
            role="img"
            aria-label={t("results.calibration.chartLabel")}
          >
            {[0, 0.25, 0.5, 0.75, 1].map((v) => (
              <g key={v}>
                <line x1="50" x2="548" y1={245 - v * 210} y2={245 - v * 210} />
                <text x="40" y={249 - v * 210} textAnchor="end">
                  {fmt.percent(v, 0)}
                </text>
              </g>
            ))}
            <path d="M50 245L548 35" className="ideal" />
            {m.reliability.map((b, i) => (
              <g key={i}>
                <rect
                  x={52 + i * 49.6}
                  y={245 - b.accuracy * 210}
                  width="37"
                  height={b.accuracy * 210}
                  className={b.count ? "bar" : "empty-bar"}
                />
                <text x={70 + i * 49.6} y="265" textAnchor="middle">
                  {(i + 1) * 10}
                </text>
                <text
                  x={70 + i * 49.6}
                  y={Math.max(22, 236 - b.accuracy * 210)}
                  textAnchor="middle"
                  className="bin-count"
                >
                  {b.count || ""}
                </text>
              </g>
            ))}
          </svg>
          <div className="chart-foot">
            <span>{t("results.calibration.axes")}</span>
            <span>{t("results.calibration.barCounts")}</span>
          </div><p className="small muted">{t("results.calibration.footnote")}</p>
        </section>
        <section className="analysis-panel">
          <div className="section-title">
            <div>
              <h2>{t("results.breakdown.title")}</h2>
              <p>{t("results.breakdown.intro")}</p>
            </div>
          </div>
          <div className="family-bars">
            {Object.entries(m.families).map(([name, f]) => (
              <div key={name}>
                <div>
                  <span>{familyLabel(t, name)}</span>
                  <strong>{fmt.percent(f.correct / f.total)}</strong>
                </div>
                <div className="wide-track">
                  <i style={{ width: `${(f.correct / f.total) * 100}%` }} />
                </div>
                <small>
                  {t("results.breakdown.counts", { correct: f.correct, total: f.total, failed: f.failed })}
                </small>
              </div>
            ))}
          </div>
        </section>
      </div>
      <div className="results-grid">
        <section className="analysis-panel">
          <h2>{t("results.technical.title")}</h2>
          <div className="ledger">
            {[
              [t("results.metrics.macroF1"), fixedOrNull(m.macro_f1, 3)],
              [t("results.metrics.binaryBrier"), fixedOrNull(m.brier_binary, 4)],
              [t("results.metrics.multiclassBrier"), fixedOrNull(m.brier_multiclass, 4)],
              [t("results.metrics.negativeLogLoss"), fixedOrNull(m.nll, 4)],
              [t("results.metrics.expectedScoreMae"), fixedOrNull(m.ordinal_mae, 4)],
              [t("results.technical.answerMatchesOriginal"), fmt.percent(m.selected_label_accuracy)],
              [t("results.technical.correctUsableOriginal"), fmt.percent(m.accuracy)],
              [
                t("results.technical.contractFailures"),
                fmt.number(m.output_contract_failures),
              ],
              [t("results.technical.unsupported"), fmt.number(m.unsupported)],
              [t("results.technical.teacherExcluded"), fmt.number(m.teacher_count)],
              [t("results.technical.correctUsableShared"), fmt.percent(e.matched?.accuracy)],
              [
                t("results.technical.sharedInputs"),
                `${fmt.number(result.matched_count)} / ${fmt.number(result.case_count)}`,
              ],
              [t("results.technical.sharedAnswerKey"), fmt.number(e.matched?.verified_count)],
            ].map(([a, b]) => (
              <div key={a}>
                <span>{a}</span>
                <strong>{b ?? t("common.notApplicable")}</strong>
              </div>
            ))}
          </div>
          <p className="muted small">{t("results.technical.strictNote")}</p>
        </section>
        <section className="analysis-panel">
          <div className="section-title">
            <h2>{t("results.judge.title")}</h2>
            <span className="tag">{"CODEX CLI"}</span>
          </div>
          <div className="judge-summary">
            <ShieldCheck size={34} />
            <strong>
              {reviews.length}
              <span>{t("results.judge.judgments")}</span>
            </strong>
          </div>
          <p className="muted">
            {reviews.length ? t("results.judge.acceptedInSample", { n: accepted }) + " " : ""}
            {t("results.judge.explanation")}
          </p>
          <div className="audit-list">
            {reviews.slice(0, 3).map((j) => (
              <div key={j.job_id}>
                <span className="accent">
                  {verdictLabel(j.data.grade?.verdict || "")}
                </span>
                <p>{j.data.grade?.rationale}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
      <Operations result={result} model={e.id} />
      <div className="limitations">
        <TriangleAlert size={18} />
        <div>
          <strong>{t("results.scope.title")}</strong>
          {result.limitations.map((s) => (
            <p key={s}>{s}</p>
          ))}
          <p>{t("results.scope.teacherAgreement")}</p>
        </div>
      </div>
    </>
  );
}

function Replay({
  rid,
  result,
}: {
  rid: string | null;
  result: Result | null;
}) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const [timeline, setTimeline] = useState<ArenaEvent[]>([]),
    [playing, setPlaying] = useState(false),
    [clock, setClock] = useState(0),
    [speed, setSpeed] = useState(1);

  useEffect(() => {
    setClock(0);
    setPlaying(false);
    if (rid) api<ArenaEvent[]>(`/runs/${rid}/timeline`).then(setTimeline);
  }, [rid]);

  const lanes = useMemo(() => {
    const values =
      result?.entrants.slice(0, 4).map((e) => ({
        id: e.id,
        name: e.name,
        events: timeline.filter(
          (ev) => ev.kind === "prediction" && ev.data.model_id === e.id,
        ),
      })) || [];
    return values.map((v) => {
      let total = 0;
      return {
        ...v,
        points: v.events.map((ev) => {
          total += Number(ev.data.request_ms) || 0;
          return { time: total, event: ev };
        }),
        total,
      };
    });
  }, [timeline, result]);

  const duration = Math.max(1, ...lanes.map((l) => l.total));

  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(
      () =>
        setClock((c) => {
          if (c + 100 * speed >= duration) {
            setPlaying(false);
            return duration;
          }
          return c + 100 * speed;
        }),
      100,
    );
    return () => clearInterval(timer);
  }, [playing, speed, duration]);

  if (!rid || !result)
    return (
      <Empty
        icon={Play}
        title={t("replay.emptyTitle")}
        detail={t("replay.emptyDetail")}
      />
    );

  return (
    <>
      <div className="replay-controls">
        <span className="tag measured">{t("replay.tag")}</span>
        <span>{t("replay.scopeNote")}</span>
        <div>
          <button
            className="icon-btn"
            onClick={() => {
              setClock(0);
              setPlaying(false);
            }}
            aria-label={t("replay.restart")}
          >
            <RotateCcw size={17} />
          </button>
          <button
            className="button primary compact"
            onClick={() => {
              if (clock === duration) setClock(0);
              setPlaying(!playing);
            }}
          >
            {playing ? <Pause size={16} /> : <Play size={16} />}{" "}
            {playing ? t("replay.pause") : t("replay.play")}
          </button>
          <select
            value={speed}
            aria-label={t("replay.speed")}
            onChange={(e) => setSpeed(Number(e.target.value))}
          >
            {[0.5, 1, 2, 5, 10].map((n) => (
              <option value={n} key={n}>
                {fmt.number(n, 1)}×
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="replay-timer">
        <strong>
          {fmt.fixed(clock / 1000, 1)}
          <small>{"s"}</small>
        </strong>
        <span>{t("replay.playback", { speed: fmt.number(speed, 1) })}</span>
      </div>
      <input
        className="timeline-slider"
        aria-label={t("replay.position")}
        type="range"
        min="0"
        max={duration}
        value={clock}
        onChange={(e) => setClock(Number(e.target.value))}
      />
      <div className="replay-lanes">
        {lanes.map((lane, i) => {
          const done = lane.points.filter((p) => p.time <= clock),
            last = done.at(-1);
          return (
            <section key={lane.id}>
              <div className="lane-heading">
                <span>{t("replay.lane", { n: String(i + 1).padStart(2, "0") })}</span>
                <h2>{lane.name}</h2>
              </div>
              <div className="lane-value">
                {String(done.length).padStart(2, "0")}
                <span>{t("replay.decisions", { n: lane.points.length })}</span>
              </div>
              <div className="decision-matrix">
                {lane.points.map((p, index) => (
                  <i
                    title={String(p.event.data.case_id)}
                    key={index}
                    className={
                      p.time <= clock
                        ? p.event.data.status === "ok"
                          ? "done"
                          : "failed"
                        : ""
                    }
                  />
                ))}
              </div>
              <div className="lane-current">
                <span className="field-label">{t("replay.latestDecision")}</span>
                <strong>
                  {last
                    ? String(last.event.data.selected || last.event.data.status)
                    : t("replay.waiting")}
                </strong>
                <small>
                  {last ? String(last.event.data.case_id) : t("replay.aligned")}
                </small>
              </div>
              <div className="lane-footer">
                <Timer size={15} />
                <span>{t("replay.totalRequestTime", { time: fmt.duration(lane.total) })}</span>
              </div>
            </section>
          );
        })}
      </div>
      <div className="limitations">
        <Activity size={18} />
        <p>{t("replay.sequentialNote")}</p>
      </div>
    </>
  );
}

function Setup({
  ready,
  selected,
  toggle,
  onRefresh,
  onError,
  onLocal,
}: {
  ready: Ready | null;
  selected: string[];
  toggle: (s: string) => void;
  onRefresh: () => Promise<void>;
  onError: (s: string) => void;
  onLocal: () => void;
}) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const [checking, setChecking] = useState(false);
  // Judge-check failures carry untranslated prose from arena/judge.py, so they are shown here as English-only.
  const [judgeError, setJudgeError] = useState("");

  if (!ready)
    return (
      <Empty
        icon={Cpu}
        title={t("setup.emptyTitle")}
        detail={t("setup.emptyDetail")}
      />
    );

  // Hoisted so the extractor sees these keys (it skips t() calls nested in another t()'s options).
  const judgeVersion = ready.judge.version || t("setup.notInstalled");
  const observedModel = ready.judge.observed_model || t("setup.observedNotExposed");

  async function prepare() {
    try {
      await api("/setup/prepare", {
        model_ids: selected.filter(
          (m) => !ready?.models.find((x) => x.id === m)?.hosted,
        ),
      });
      await onRefresh();
    } catch (e) {
      onError(errorText(t, e));
    }
  }

  async function check() {
    setChecking(true);
    setJudgeError("");
    try {
      await api("/setup/judge-check", {});
      await onRefresh();
    } catch (e) {
      setJudgeError(errorText(t, e));
    } finally {
      setChecking(false);
    }
  }

  const dataLanguage = fmt.languageName(ready.suites.language || "en");
  const slotStatus = (s: Ready["suites"]["slots"][number]) =>
    s.ready
      ? t("status.ready")
      : s.expected == null
        ? t("setup.testData.notInSuite")
        : t("setup.testData.count", { available: fmt.number(s.available ?? 0), expected: fmt.number(s.expected) });

  return (
    <>
      <div className="setup-summary">
        <div>
          <Cpu size={28} />
          <span>
            {t("setup.compute")}
            <strong>
              {ready.hardware.gpu?.name || t("setup.noGpu")}
            </strong>
            <small>
              {t("setup.diskFree", { n: fmt.number(ready.hardware.disk_free_gb) })} ·{" "}
              {ready.docker_ready
                ? t("setup.workerReady")
                : t("setup.workerRequired")}
            </small>
          </span>
        </div>
        <div>
          <Terminal size={28} />
          <span>
            {t("setup.judge")}<strong>{"GPT-6 Astra · Codex CLI"}</strong>
            <small>
              {ready.judge.smoke_passed
                ? t("setup.judgeSmokePassed")
                : ready.judge.ready
                  ? t("setup.judgeLoginFound")
                  : t("setup.judgeLoginRequired")}
            </small>
            {judgeError && (
              <EnglishOnly>
                <small role="alert">{judgeError}</small>
              </EnglishOnly>
            )}
          </span>
          <button
            className="button secondary compact"
            onClick={check}
            disabled={checking || !!offline}
          >
            {checking ? t("setup.checking") : t("setup.verifyJudge")}
          </button>
        </div>
      </div>
      <div className="section-title setup-title">
        <div>
          <h2>{t("setup.roster")}</h2>
          <p>{t("setup.rosterNote")}</p>
        </div>
        <div className="heading-actions">
          <button className="button secondary compact" onClick={onLocal}>
            {t("setup.useLocal")} <ArrowRight size={15} />
          </button>
          <button
            className="button primary compact"
            onClick={prepare}
            disabled={ready.setup.status === "preparing" || !!offline}
          >
            <ArrowDownToLine size={16} />
            {ready.setup.status === "preparing"
              ? t("setup.preparing")
              : t("setup.prepareSelected")}
          </button>
        </div>
      </div>
      {ready.setup.message && (
        <div className="setup-progress">
          <Activity size={16} />
          <EnglishOnly>{ready.setup.message}</EnglishOnly>
        </div>
      )}
      <div className="table-scroll">
        <table className="setup-table">
          <thead>
            <tr>
              <th>{t("setup.columns.entrant")}</th>
              <th>{t("setup.columns.execution")}</th>
              <th>{t("setup.columns.revision")}</th>
              <th>{t("setup.columns.limits")}</th>
              <th>{t("setup.columns.readiness")}</th>
            </tr>
          </thead>
          <tbody>
            {ready.models.map((m) => (
              <tr key={m.id}>
                <td>
                  <label>
                    <input
                      type="checkbox"
                      checked={selected.includes(m.id)}
                      onChange={() => toggle(m.id)}
                    />
                    <div className="model-name">
                      {m.name}
                      <small>
                        {m.family} · {m.license}
                      </small>
                    </div>
                  </label>
                </td>
                <td>
                  {m.hosted ? t("setup.hosted") : m.size + " · " + m.precision}
                </td>
                <td className="mono">
                  {(m.resolved_revision || m.revision).slice(0, 12)}
                  {m.repo && (
                    <a
                      title={t("setup.openModelCard")}
                      aria-label={t("setup.openModelCardFor", { name: m.name })}
                      href={`https://huggingface.co/${m.repo}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <ArrowUpRight size={12} />
                    </a>
                  )}
                </td>
                <td>
                  {t("setup.limits", { options: m.max_options, tokens: fmt.number(m.context) })}
                </td>
                <td>
                  <span className={m.ready ? "accent" : "muted"}>
                    {m.ready ? <Check size={13} /> : <Circle size={10} />}{" "}
                    {m.ready
                      ? t("status.ready")
                      : m.reason_code
                        ? t(`readiness.${m.reason_code}`, { defaultValue: m.reason ?? undefined })
                        : m.reason}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {ready.suites.slots?.length > 0 && (
        <section className="test-data">
          <div className="section-title">
            <div>
              <h2>{t("setup.testData.title", { language: dataLanguage })}</h2>
              <p>{t("setup.testData.hint")}</p>
            </div>
            <Database size={20} />
          </div>
          <div className="table-scroll">
            <table className="setup-table data-slots">
              <thead>
                <tr>
                  <th>{t("setup.testData.columns.slot")}</th>
                  <th>{t("setup.testData.columns.family")}</th>
                  <th>{t("setup.testData.columns.source")}</th>
                  <th>{t("setup.testData.columns.status")}</th>
                  <th>{t("setup.testData.columns.licence")}</th>
                </tr>
              </thead>
              <tbody>
                {ready.suites.slots.map((s) => (
                  <tr key={s.slot}>
                    <td>
                      <div className="model-name">
                        {packLabel(t, s.pack)}
                        <small className="mono">{s.slot}</small>
                      </div>
                    </td>
                    <td>{familyLabel(t, s.family)}</td>
                    <td>{t(`setup.testData.sources.${s.source}`, { defaultValue: s.source })}</td>
                    <td>
                      <span className={s.ready ? "accent" : "muted"}>
                        {s.ready ? <Check size={13} /> : <Circle size={10} />} {slotStatus(s)}
                      </span>
                      {s.source === "missing" && s.reason && (
                        <EnglishOnly>
                          <small className="muted slot-reason">{s.reason}</small>
                        </EnglishOnly>
                      )}
                    </td>
                    <td className="small muted">{s.licence || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      <div className="setup-bottom">
        <section>
          <div className="section-title">
            <div>
              <h2>{t("setup.frozenSuite")}</h2>
              <p>
                {t("setup.decisionsPrepared", {
                  available: fmt.number(ready.suites.available),
                  expected: fmt.number(ready.suites.expected),
                })}
              </p>
            </div>
            <Database size={20} />
          </div>
          {ready.suites.packs.map((p) => (
            <div className="pack-row" key={p.name}>
              <span>
                {p.ready ? <CheckCircle2 size={15} /> : <Circle size={15} />}{" "}
                {packLabel(t, p.name)}
              </span>
              <strong>
                {fmt.number(p.available)} <small>/ {fmt.number(p.expected)}</small>
              </strong>
            </div>
          ))}
        </section>
        <section>
          <h2>{t("setup.connections")}</h2>
          <div className="connection">
            <Terminal size={19} />
            <div>
              <strong>{"Codex CLI"}</strong>
              <p>
                {t("setup.chatgptAuth", { version: judgeVersion })}
              </p>
              <small>
                {t("setup.requestedModel", { model: "gpt-6-astra" })}
                <br />
                {t("setup.observedModel", { id: observedModel })}
              </small>
            </div>
          </div>
          <div className="connection">
            <Zap size={19} />
            <div>
              <strong>{"TypeSafe / Jev"}</strong>
              <p>
                {ready.models.find((m) => m.id === "jev")?.ready
                  ? t("setup.typesafeKeyConfigured")
                  : t("setup.typesafeKeyMissing")}
              </p>
              <a href="https://typesafe.ai" target="_blank" rel="noreferrer">
                {t("setup.typesafeAccount")} <ExternalLink size={12} />
              </a>
            </div>
          </div>
          <p className="muted small">{t("setup.keysNote")}</p>
          <EnglishOnly>
            <p className="muted small">{ready.suites.fresh_status}</p>
          </EnglishOnly>
        </section>
      </div>
    </>
  );
}

function Empty({
  icon: Icon,
  title,
  detail,
}: {
  icon: typeof Activity;
  title: string;
  detail: string;
}) {
  return (
    <div className="empty-state">
      <Icon size={36} />
      <h2>{title}</h2>
      <p>{detail}</p>
    </div>
  );
}

(async () => {
  const state = await api<{ language: string; locales: LocaleInfo[] }>("/i18n").catch(() => ({ language: "en", locales: [] }));
  const bundled = new Set(bundledLocales.map((l) => l.code));
  const locales = state.locales.filter((l) => bundled.has(l.code));
  await initI18n(bundled.has(state.language) ? state.language : "en");
  createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <NavigationProvider><App locales={locales} /></NavigationProvider>
    </React.StrictMode>,
  );
})();

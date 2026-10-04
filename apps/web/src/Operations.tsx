import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Play,
  Pause,
  RotateCcw,
  Timer,
  ArrowRight,
  Check,
  TriangleAlert,
} from "lucide-react";
import type { TFunction } from "i18next";
import { Trans } from "react-i18next";
import type { Result, Episode } from "./types";
import { useTranslation, useFormat } from "./i18n";
import { answerId, slug } from "./labels";
import referenceCautions from "../../../docs/reference-cautions.json";

// Episode answers and topics are data values compared in code; only their display text is translated.
// Non-English runs store the localized label in `answer`; compare and look up labels by answerId(step).
const directionLabel = (t: TFunction, d: string) =>
  t(`operations.directions.${d}`, { defaultValue: d });
const queueLabel = (t: TFunction, q: string) =>
  t(`operations.queues.${slug(q)}`, { defaultValue: q });
const topicLabel = (t: TFunction, topic: string) =>
  t(`operations.topics.${slug(topic)}`, { defaultValue: topic });

export function Operations({
  result,
  model,
}: {
  result: Result;
  model: string;
}) {
  const perf = result.performance?.[model],
    episodes = (result.episodes || []).filter((e) => e.model_id === model);
  const m = result.entrants.find((e) => e.id === model)?.metrics;
  const caution = referenceCautions.applicability.find(
    (profile) => profile.case_sha256 === result.manifest?.case_sha256,
  );
  const { t } = useTranslation();
  const fmt = useFormat();
  const na = t("common.notApplicable");
  const pct = (n: number | null | undefined) =>
    n == null ? na : fmt.percent(n, 1);
  const fixedOrNa = (n: number | null | undefined, d: number) =>
    n == null ? na : fmt.fixed(n, d);
  return (
    <>
      <section className="analysis-panel operation-panel">
        <div className="section-title">
          <div>
            <h2>{t("operations.performanceTitle")}</h2>
            <p>{t("operations.performanceIntro")}</p>
          </div>
          <span className="tag">
            {perf ? t("operations.measured") : t("operations.fullSuiteOnly")}
          </span>
        </div>
        {perf ? (
          <>
            <div className="performance-blocks">
              {perf.blocks.map((b) => (
                <div key={b.block}>
                  <span>
                    {t("operations.block", {
                      n: b.block + 1,
                      concurrency: b.concurrency,
                    })}
                  </span>
                  <strong>
                    {fmt.fixed(b.requests_per_second, 1)}
                    <small> {t("operations.decisionsPerSecond")}</small>
                  </strong>
                  <div>
                    <span>
                      {t("operations.typical", { time: fmt.duration(b.p50_ms) })}
                    </span>
                    <span>
                      {t("operations.p95Within", {
                        time: fmt.duration(b.p95_ms),
                      })}
                    </span>
                    <span>
                      {t("operations.validRequests", {
                        valid: fmt.number(b.valid),
                        total: fmt.number(b.requests),
                      })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="fanout">
              {perf.fanout.map((f) => (
                <span key={f.questions}>
                  <Trans
                    i18nKey="operations.fanout"
                    values={{ n: fmt.number(f.questions) }}
                    components={{ b: <b /> }}
                  />{" "}
                  <ArrowRight size={13} />
                  <strong>{fmt.duration(f.elapsed_ms)}</strong>
                </span>
              ))}
            </div>
            <p className="small muted">{t("operations.serialProfileNote")}</p>
          </>
        ) : (
          <p className="muted small">{t("operations.fullSuiteHint")}</p>
        )}
      </section>
      <section className="analysis-panel operation-panel">
        <div className="section-title">
          <div>
            <h2>{t("operations.pairedTitle")}</h2>
            <p>{t("operations.pairedIntro")}</p>
          </div>
        </div>
        {result.comparisons.filter((c) => c.model === model).length ? (
          <div className="ledger">
            {result.comparisons
              .filter((c) => c.model === model)
              .map((c) => (
                <div key={c.reference}>
                  <span>
                    {t("operations.versus", {
                      name:
                        result.entrants.find((e) => e.id === c.reference)
                          ?.name || c.reference,
                      count: c.n,
                      n: fmt.number(c.n),
                    })}
                  </span>
                  <strong>
                    {c.delta == null
                      ? na
                      : `${fmt.points(c.delta)} ${t("common.pp")}`}
                    {c.ci && (
                      <small>
                        {" "}
                        {t("operations.ciRange", {
                          low: fmt.fixed(c.ci[0] * 100, 1),
                          high: fmt.fixed(c.ci[1] * 100, 1),
                        })}
                      </small>
                    )}
                  </strong>
                </div>
              ))}
          </div>
        ) : (
          <p className="muted small">{t("operations.pairedEmpty")}</p>
        )}
      </section>
      <div className="results-grid">
        <section className="analysis-panel">
          <h2>{t("operations.referenceTitle")}</h2>
          <div className="ledger">
            <div>
              <span>{t("operations.teacherAgreement")}</span>
              <strong>{pct(m?.teacher_agreement)}</strong>
            </div>
            <div>
              <span>{t("operations.teacherProbabilityDifference")}</span>
              <strong>{fixedOrNa(m?.teacher_brier, 4)}</strong>
            </div>
            <div>
              <span>{t("operations.packMacroAccuracy")}</span>
              <strong>{pct(m?.pack_macro_accuracy)}</strong>
            </div>
            <div>
              <span>{t("operations.scifactNdcg")}</span>
              <strong>{fixedOrNa(m?.diagnostics?.rag.ndcg_at_10, 3)}</strong>
            </div>
            <div>
              <span>{t("operations.scifactMrr")}</span>
              <strong>{fixedOrNa(m?.diagnostics?.rag.mrr, 3)}</strong>
            </div>
            <div>
              <span>{t("operations.completeQueryPools")}</span>
              <strong>{fmt.number(m?.diagnostics?.rag.queries || 0)}</strong>
            </div>
          </div>
        </section>
        <section className="analysis-panel">
          <h2>{t("operations.workflowTitle")}</h2>
          {episodes.length ? (
            ["untimed_quality", "deadline_500ms"]
              .filter((mode) => episodes.some((e) => e.mode === mode))
              .map((mode) => {
                const rows = episodes.filter((e) => e.mode === mode);
                const ticketEpisodes = rows.filter((e) => e.task === "tickets");
                const warehouseEpisodes = rows.filter(
                  (e) => e.task === "warehouse",
                );
                const tickets = ticketEpisodes.flatMap((e) => e.trace);
                const unrestricted = tickets.filter((step) => !step.restricted);
                return (
                  <div className="episode-score" key={mode}>
                    <span>
                      {mode === "untimed_quality"
                        ? t("operations.modes.untimedQuality")
                        : t("operations.modes.decisionDeadline")}
                    </span>
                    <strong>
                      {fmt.number(rows.filter((e) => e.success).length)}
                      <small>
                        {" "}
                        {t("operations.successfulEpisodes", {
                          total: fmt.number(rows.length),
                        })}
                      </small>
                    </strong>
                    <p>
                      {t("operations.successByTask", {
                        warehouse: fmt.number(
                          warehouseEpisodes.filter((e) => e.success).length,
                        ),
                        warehouseTotal: fmt.number(warehouseEpisodes.length),
                        tickets: fmt.number(
                          ticketEpisodes.filter((e) => e.success).length,
                        ),
                        ticketsTotal: fmt.number(ticketEpisodes.length),
                      })}
                    </p>
                    <p>
                      {t("operations.ticketDecisions", {
                        correct: fmt.number(
                          tickets.filter((step) => step.correct).length,
                        ),
                        total: fmt.number(tickets.length),
                        review: fmt.number(
                          unrestricted.filter(
                            (step) => answerId(step) === "Review",
                          ).length,
                        ),
                        unrestricted: fmt.number(unrestricted.length),
                      })}
                    </p>
                    <p>
                      {t("operations.violationsAndMisses", {
                        violations: fmt.number(
                          rows.reduce((s, e) => s + e.violations, 0),
                        ),
                        misses: fmt.number(
                          rows.reduce(
                            (s, e) => s + (e.deadline_misses || 0),
                            0,
                          ),
                        ),
                      })}
                    </p>
                  </div>
                );
              })
          ) : (
            <p className="small muted spaced">
              {t("operations.noEpisodes")}
            </p>
          )}
          <p className="small muted">{t("operations.ticketSuccessNote")}</p>
        </section>
      </div>
      {m?.diagnostics && (
        <div className="results-grid">
          <section className="analysis-panel">
            <h2>{t("operations.coverageTitle")}</h2>
            <p className="small muted spaced">
              {t("operations.coverageNote", {
                n: fmt.number(result.case_count),
              })}
            </p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>{t("operations.minConfidence")}</th>
                    <th>{t("operations.coverage")}</th>
                    <th>{t("operations.error")}</th>
                  </tr>
                </thead>
                <tbody>
                  {m.diagnostics.coverage_error.map((r) => (
                    <tr key={r.threshold}>
                      <td>{pct(r.threshold)}</td>
                      <td>{pct(r.coverage)}</td>
                      <td>{pct(r.error)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="analysis-panel">
            <h2>{t("operations.robustnessTitle")}</h2>
            <p className="small muted spaced">
              {t("operations.robustnessIntro")}
            </p>
            <div className="ledger">
              {Object.entries(m.diagnostics.robustness).map(([name, r]) => (
                <div key={name}>
                  <span>
                    {t("operations.robustnessPairs", {
                      name,
                      pairs: fmt.number(r.pairs),
                    })}
                  </span>
                  <strong>
                    {`${fmt.points(r.accuracy_delta)} ${t("common.pp")}`}
                    <small>
                      {" "}
                      {t("operations.answerFlips", {
                        rate: pct(r.answer_flip_rate),
                      })}
                    </small>
                  </strong>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
      {caution && (
        <section className="analysis-panel operation-panel">
          <div className="section-title">
            <h2>{t("operations.cautionTitle")}</h2>
            <TriangleAlert size={18} />
          </div>
          <p className="small muted">
            {t("operations.cautionBody", {
              count: caution.affected_cases,
              n: fmt.number(caution.affected_cases),
            })}
          </p>
        </section>
      )}
    </>
  );
}

export function EpisodeReplay({ result }: { result: Result }) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const episodes = result.episodes || [];
  const [task, setTask] = useState("warehouse"),
    [seed, setSeed] = useState(5090),
    [mode, setMode] = useState("untimed_quality"),
    [chosen, setChosen] = useState<string[]>([]),
    [playing, setPlaying] = useState(false),
    [clock, setClock] = useState(0),
    [speed, setSpeed] = useState(1);
  const available = result.entrants.filter((e) =>
    episodes.some((p) => p.model_id === e.id),
  );
  useEffect(() => {
    setChosen([]);
    setClock(0);
    setPlaying(false);
  }, [result.run_id]);
  useEffect(() => {
    setChosen((old) =>
      old.length
        ? old
        : [
            "laya",
            "decider",
            "winnow",
            "nimble",
            "plumb",
            "semif",
            "clm",
            "qwen",
            "nli",
            "laya-typed",
            "laya-multi",
            "uniform",
          ]
            .filter((id) => available.some((e) => e.id === id))
            .slice(0, 4),
    );
  }, [result.run_id, episodes.length]);
  const lanes = useMemo(
    () =>
      available
        .filter((e) => chosen.includes(e.id))
        .map((e) => ({
          name: e.name,
          episode: episodes.find(
            (p) =>
              p.model_id === e.id &&
              p.task === task &&
              p.seed === seed &&
              p.mode === mode,
          ),
        }))
        .filter((e) => e.episode)
        .map((e) => {
          let elapsed = 0;
          return {
            ...e,
            episode: e.episode!,
            points: e.episode!.trace.map((step) => ({
              time: (elapsed += step.request_ms),
              step,
            })),
            duration: e.episode!.wall_request_ms,
          };
        }),
    [episodes, chosen, task, seed, mode],
  );
  const duration = Math.max(1, ...lanes.map((l) => l.duration));
  useEffect(() => {
    setClock(0);
    setPlaying(false);
  }, [task, seed, mode, chosen]);
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(
      () =>
        setClock((c) => {
          const n = Math.min(duration, c + 50 * speed);
          if (n === duration) setPlaying(false);
          return n;
        }),
      50,
    );
    return () => clearInterval(timer);
  }, [playing, speed, duration]);
  if (!episodes.length)
    return (
      <div className="empty-state">
        <Box size={36} />
        <h2>{t("operations.replay.emptyTitle")}</h2>
        <p>{t("operations.replay.emptyDetail")}</p>
      </div>
    );
  return (
    <>
      <section className="replay-intro">
        <h2>{t("operations.replay.introTitle")}</h2>
        <p>{t("operations.replay.introBody")}</p>
        <p className="small muted">{t("operations.replay.introNote")}</p>
      </section>
      <div className="episode-controls">
        <div className="workspace-tabs">
          {["warehouse", "tickets"].map((k) => (
            <button
              key={k}
              className={task === k ? "selected" : ""}
              onClick={() => setTask(k)}
            >
              {k === "warehouse"
                ? t("operations.replay.warehouseTask")
                : t("operations.replay.ticketTask")}
            </button>
          ))}
        </div>
        <div>
          <select
            aria-label={t("operations.replay.seedLabel")}
            value={seed}
            onChange={(e) => setSeed(+e.target.value)}
          >
            {[...new Set(episodes.map((e) => e.seed))].sort().map((s) => (
              <option key={s} value={s}>
                {t("operations.replay.seed", { seed: s })}
              </option>
            ))}
          </select>
          <select
            aria-label={t("operations.replay.modeLabel")}
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            {[...new Set(episodes.map((e) => e.mode))].map((m) => (
              <option key={m} value={m}>
                {m === "untimed_quality"
                  ? t("operations.modes.untimedQuality")
                  : t("operations.modes.deadline")}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="lane-picker">
        {available.map((e) => (
          <button
            key={e.id}
            className={chosen.includes(e.id) ? "selected" : ""}
            onClick={() =>
              setChosen((c) =>
                c.includes(e.id)
                  ? c.filter((x) => x !== e.id)
                  : c.length < 4
                    ? [...c, e.id]
                    : [...c.slice(1), e.id],
              )
            }
          >
            {chosen.includes(e.id) && <Check size={12} />} {e.name}
          </button>
        ))}
        <span>{t("operations.replay.chooseLanes")}</span>
      </div>
      <div className="replay-controls">
        <span className="tag measured">{t("operations.replay.tag")}</span>
        <span>
          {t("operations.replay.playbackInfo", {
            speed: fmt.number(speed, 2),
          })}
        </span>
        <div>
          <button
            className="icon-btn"
            aria-label={t("operations.replay.restart")}
            onClick={() => {
              setClock(0);
              setPlaying(false);
            }}
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
            aria-label={t("operations.replay.speed")}
            value={speed}
            onChange={(e) => setSpeed(+e.target.value)}
          >
            {[0.1, 0.25, 0.5, 1, 2, 5, 10].map((n) => (
              <option key={n} value={n}>
                {fmt.number(n, 2)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="replay-timer">
        <strong>
          {fmt.fixed(clock / 1000, 2)}
          <small>{"s"}</small>
        </strong>
        <span>
          {t("operations.replay.recorded", { time: fmt.duration(duration) })}
        </span>
      </div>
      <input
        className="timeline-slider"
        aria-label={t("operations.replay.position")}
        type="range"
        min={0}
        max={duration}
        value={clock}
        onChange={(e) => setClock(+e.target.value)}
      />
      <div
        className="world-lanes"
        style={{
          gridTemplateColumns: `repeat(${Math.max(1, lanes.length)},minmax(0,1fr))`,
        }}
      >
        {lanes.map((l, i) => {
          const done = l.points.filter((p) => p.time <= clock),
            last = done.at(-1)?.step,
            finished = done.length === l.points.length;
          return (
            <section key={l.episode.model_id}>
              <div className="world-title">
                <span>
                  {t("replay.lane", { n: String(i + 1).padStart(2, "0") })}
                </span>
                <h2>{l.name}</h2>
                <span className="tag">
                  {finished
                    ? l.episode.success
                      ? t("operations.replay.success")
                      : t("operations.replay.incomplete")
                    : t("operations.replay.step", {
                        done: fmt.number(done.length),
                        total: fmt.number(l.points.length),
                      })}
                </span>
              </div>
              {task === "warehouse" ? (
                <WarehouseGrid
                  episode={l.episode}
                  steps={done.map((d) => d.step)}
                />
              ) : (
                <TicketBoard
                  episode={l.episode}
                  steps={done.map((d) => d.step)}
                />
              )}
              <div className="world-decision">
                <span>{t("replay.latestDecision")}</span>
                <strong>
                  {last?.answer
                    ? task === "warehouse"
                      ? directionLabel(t, answerId(last)!)
                      : queueLabel(t, answerId(last)!)
                    : "—"}
                  {last?.deadline_missed && <TriangleAlert size={16} />}
                </strong>
                <small>
                  {last
                    ? last.deadline_missed
                      ? t("operations.replay.deadlineMissed", {
                          time: fmt.duration(last.request_ms),
                        })
                      : fmt.duration(last.request_ms)
                    : t("operations.replay.waitingFirst")}
                </small>
              </div>
              <div className="world-metrics">
                <span>
                  <Trans
                    i18nKey="operations.replay.steps"
                    values={{ n: fmt.number(done.length) }}
                    components={{ b: <b /> }}
                  />
                </span>
                <span>
                  <Trans
                    i18nKey="operations.replay.failedActions"
                    values={{
                      n: fmt.number(
                        done.filter(
                          (d) =>
                            d.step.valid === false ||
                            d.step.correct === false,
                        ).length,
                      ),
                    }}
                    components={{ b: <b /> }}
                  />
                </span>
                <span>
                  <Timer size={13} />{" "}
                  {fmt.duration(finished ? l.duration : clock)}
                </span>
              </div>
            </section>
          );
        })}
      </div>
      <p className="muted small spaced">{t("operations.replay.deadlineNote")}</p>
    </>
  );
}

function WarehouseGrid({
  episode,
  steps,
}: {
  episode: Episode;
  steps: Episode["trace"];
}) {
  const { t } = useTranslation();
  const position = steps.at(-1)?.after || [0, 0],
    goal = episode.goal || [5, 5],
    path = [[0, 0], ...steps.map((s) => s.after || [0, 0])];
  return (
    <svg
      viewBox="0 0 300 300"
      className="warehouse-grid"
      role="img"
      aria-label={t("operations.replay.robotPosition", {
        position: position.join(","),
        goal: goal.join(","),
      })}
    >
      <defs>
        <pattern
          id={`grid-${episode.model_id}`}
          width="50"
          height="50"
          patternUnits="userSpaceOnUse"
        >
          <rect
            width="50"
            height="50"
            fill="none"
            stroke="var(--line)"
            strokeWidth="1"
          />
        </pattern>
      </defs>
      <rect width="300" height="300" fill={`url(#grid-${episode.model_id})`} />
      {(episode.blocked || []).map(([x, y]) => (
        <g key={`${x}-${y}`}>
          <rect
            x={x * 50 + 5}
            y={y * 50 + 5}
            width="40"
            height="40"
            rx="3"
            fill="var(--obstacle)"
          />
          <path
            d={`M${x * 50 + 12} ${y * 50 + 12}l26 26m0-26l-26 26`}
            stroke="#55555c"
          />
        </g>
      ))}
      <rect
        x={goal[0] * 50 + 7}
        y={goal[1] * 50 + 7}
        width="36"
        height="36"
        rx="4"
        fill="var(--accent-soft)"
        stroke="var(--accent)"
        strokeDasharray="3 3"
      />
      <text
        x={goal[0] * 50 + 25}
        y={goal[1] * 50 + 29}
        textAnchor="middle"
        fill="var(--accent)"
        fontSize="10"
      >
        {t("operations.replay.goal")}
      </text>
      <polyline
        points={path
          .map((p) => `${p[0] * 50 + 25},${p[1] * 50 + 25}`)
          .join(" ")}
        fill="none"
        stroke="var(--accent)"
        strokeWidth="3"
        opacity=".45"
      />
      <circle
        cx={position[0] * 50 + 25}
        cy={position[1] * 50 + 25}
        r="15"
        fill="var(--accent-soft)"
      />
      <circle
        cx={position[0] * 50 + 25}
        cy={position[1] * 50 + 25}
        r="8"
        fill="var(--accent)"
      />
      <circle cx={25} cy={25} r="3" fill="var(--ink)" />
    </svg>
  );
}

function TicketBoard({
  episode,
  steps,
}: {
  episode: Episode;
  steps: Episode["trace"];
}) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const active = steps.at(-1);
  return (
    <div className="ticket-world">
      <div className="ticket-feed">
        <span>
          {t("operations.replay.incoming", {
            done: fmt.number(steps.length),
            total: fmt.number(episode.steps),
          })}
        </span>
        <strong>
          {active?.topic
            ? topicLabel(t, active.topic)
            : t("operations.replay.awaitingTicket")}
        </strong>
        <small>
          {active?.restricted
            ? t("operations.replay.restricted")
            : t("operations.replay.routeByPolicy")}
        </small>
      </div>
      <ArrowRight className="ticket-arrow" size={20} />
      <div className="ticket-queues">
        {["Billing", "Engineering", "Success", "Review"].map((queue) => (
          <div
            key={queue}
            className={answerId(active) === queue ? "selected" : ""}
          >
            <span>{queueLabel(t, queue)}</span>
            <strong>{steps.filter((s) => answerId(s) === queue).length}</strong>
            <div className="queue-dots">
              {steps
                .filter((s) => answerId(s) === queue)
                .map((s, i) => (
                  <i key={i} className={s.correct ? "correct" : "incorrect"} />
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

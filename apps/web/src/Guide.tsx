import { Fragment } from "react";
import type { TFunction } from "i18next";
import { useViewState } from "./ViewHistory";
import { useFormat, useTranslation } from "./i18n";
import { EnglishOnly } from "./EnglishOnly";
import catalog from "../../../docs/evidence/model-guide.json";
import taskData from "../../../docs/evidence/builder-task-breakdown.json";
import abcd from "../../../docs/evidence/abcd-dashboard-data.json";

// Paragraph-length explanatory prose stays English (spec option A). It is rendered inside <EnglishOnly>;
// translated headings and labels inside those wrappers carry the active language's `lang` attribute.
const takeawayProse = {
 localFast: "Winnow and Decider were close to Jev on shared short-input questions. Local timing blocks were about 50–60 ms versus Jev’s 245 ms, including its network trip.",
 smallModels: "English Laya matched 461/500 news labels (92.2%); Jev matched 441/500 (88.2%). Laya got 34 right that Jev missed; Jev got 14 right that Laya missed. Decider led XNLI at 84%, versus Jev’s 81.4%.",
 checkLimits: "Plumb and the tested SemIf interface accept 16 choices. Winnow’s native server accepts 64. BANKING77 requires 77: Plumb/SemIf were unsupported; Winnow’s 500 requests failed because Arena initially advertised the wrong limit. Nimble’s pinned 8K release could not fit the full ABCD handbook.",
 moreContext: "In ABCD, Jev led full-handbook action selection; Winnow led the combined next-step task. Retrieval helped Winnow’s action selection. Long-input speed also reversed the short-input pattern.",
 validate: "Correct choices can still fail a software output check. High confidence can be wrong. Keep validation, fallback handling and tests for repeated decisions in your application.",
 taskMix: "Generated policy tests and variations account for 2,440/4,635 shared questions (52.6%). Removing them in a post-hoc check leaves Decider at 1,976/2,195 and Jev at 1,974/2,195. Two answers apart; this is a sensitivity check, not a replacement headline.",
 accuracyTrap: "SciFact contains 453 irrelevant and 47 relevant documents. The first-option baseline always says “no” and misses all 47 positives. Jev finds 40/47, with 25 false positives. Inspect the errors your application actually cares about.",
};
const modelProse = {
 memory: "System RAM was not measured. All local profiles ran on the same 32 GB RTX 5090; that does not prove they require a 32 GB GPU.",
 dates: (checked: string) => `Base-model age and this decision model’s age are different. Sources checked ${checked}; results use the saved revision below, not necessarily today’s latest release.`,
};
const sourcesProse = {
 intro: "JevBench is one source. Arena adds other datasets and controlled tests. This gives broader coverage, but does not make it a standardized replacement for those original benchmarks.",
 additionalLead: "Additional original sources:",
 additionalTail: ". Exact samples and source revisions remain frozen in the evidence.",
 answerKey: "5,671 questions per model have a public or rule-derived answer key. Code scores the selected answer and checks the output format. The other 2,000 compare against answers produced by AI teachers and are excluded from headline accuracy. The shared ranking uses the same 4,635 answer-key questions supported by all 13 profiles.",
 astra: "For completed v2, Astra reviewed 879 distinct answer pairs across 300 selected questions: 250 selected across test groups and 50 extra model-disagreement cases. Those reviews look for ambiguous questions and questionable answers. They do not contribute a percentage to headline accuracy and do not automatically change the answer key. No human validation is claimed.",
 abcd: "300 held-out support conversations, five selected profiles, full handbook versus retrieved policy, and a separate simple long-context control. It asks a different question from v2 and was added later. Pooling it into the 13-profile total would give five models extra questions and impose an arbitrary task weighting. It belongs in the same dashboard with its own score.",
};
// Dataset names and the external-link mark are not translated.
const externalMark = " ↗";
const extraSources = [["SST-2","https://huggingface.co/datasets/stanfordnlp/sst2"],["AG News","https://huggingface.co/datasets/fancyzhx/ag_news"],["MASSIVE","https://github.com/alexa/massive"]];
const caseStateProse = "A readable view of the saved input. These are sections of one input, not extra questions.";
const breakdownProse = {
 intro: "Answer-label accuracy on identical supported questions within each row. Descriptive results, not proof that small differences will generalize.",
 footnote: "SciFact’s first-option baseline scores 90.6% because most documents are irrelevant; plain accuracy hides that imbalance. Arena policy tests and their variations make up 2,440 of the 4,635 shared questions and use eight recurring templates. Public training exposure is unknown. Do not use this table as a deployment guarantee.",
};
const abcdProse = {
 intro: "300 conversations. Five profiles. A separate follow-on to the 13-profile comparison. These are matches to recorded next steps, not live customer-resolution success.",
 actionNote: "300 action questions, all 30 options supplied. Unsupported capacity is shown separately.",
 combinedNote: "900 balanced checkpoints: 300 actions, 300 messages and 300 synthesized endings. Unsupported capacity is shown separately.",
 footnote: "Matches + non-matches equals the scored count. Unsupported inputs are excluded from that denominator. These five-profile ABCD results are separate from the selected Arena run.",
 ranking: "Winnow leads the combined balanced task. Jev leads full-handbook conditional action selection. Knowing when to speak is different from choosing the right action when told to act.",
 speed: "Full-handbook request medians were about 0.36s for hosted Jev, 1.57s for Qwen, 1.90s for Decider and 2.85s for Winnow. Retrieval greatly shortened local request times. Hardware, precision and caching differ.",
 noWinner: "Jev, Winnow, Decider and Qwen selected all constructed labels in the easy context control. Nimble’s 8K release supported only the shortest condition. Decider had output-format failures despite correct labels.",
 scope: "12,720 saved records; 118 blinded answer reviews over 76 questions. All 33 flagged reviews inspected; gold unchanged. Automated review is not human validation. ABCD recorded Jev usage: $1.210811196; combined with v2: $1.458954042. Candidate window: 3h16m, excluding earlier wait/preflight and subsequent audit/reporting. No fine-tuning. Full evidence remains in the separate ABCD HTML/ZIP and report.",
};

export function Takeaways({onModels,onAbcd,onAnalysis}:{onModels:()=>void;onAbcd:()=>void;onAnalysis:(jump:{pack:string;family:string;model?:string})=>void}){
 const { t, i18n } = useTranslation(); const lang = i18n.language;
 const items:[string,string,string,{label:string;jump:{pack:string;family:string}}?][]=[
 ["01",t("guide.takeaways.localFast"),takeawayProse.localFast],
 ["02",t("guide.takeaways.smallModels"),takeawayProse.smallModels,{label:t("guide.takeaways.compareNews"),jump:{pack:"Classification",family:"AG News"}}],
 ["03",t("guide.takeaways.checkLimits"),takeawayProse.checkLimits,{label:t("guide.takeaways.inspectBanking"),jump:{pack:"Classification",family:"BANKING77"}}],
 ["04",t("guide.takeaways.moreContext"),takeawayProse.moreContext],
 ["05",t("guide.takeaways.validate"),takeawayProse.validate],
 ["06",t("guide.takeaways.taskMix"),takeawayProse.taskMix],
 ["07",t("guide.takeaways.accuracyTrap"),takeawayProse.accuracyTrap,{label:t("guide.takeaways.compareRelevance"),jump:{pack:"RAG relevance",family:"SciFact"}}],
 ];
 return <section className="builder-takeaways"><div className="section-title"><div><h2>{t("guide.takeaways.title")}</h2><p>{t("guide.takeaways.lead")}</p></div></div>
 <EnglishOnly><div className="takeaway-list">
 {items.map(([n,title,prose,action])=><article key={n}><b>{n}</b><div><h3 lang={lang}>{title}</h3><p>{prose}</p>{action&&<button lang={lang} className="text-button" onClick={()=>onAnalysis(action.jump)}>{action.label}</button>}</div></article>)}
 </div></EnglishOnly><div className="guide-actions"><button className="text-button" onClick={onModels}>{t("guide.takeaways.compareModels")}</button><button className="text-button" onClick={onAbcd}>{t("guide.takeaways.exploreAbcd")}</button></div>
 </section>
}
export function ModelGuide({selected,onSelect}:{selected:string|null;onSelect:(id:string)=>void}){
 const { t, i18n } = useTranslation(); const lang = i18n.language; const fmt = useFormat();
 const m=catalog.models.find(x=>x.id===selected)||catalog.models[0];
 // [label, value, value is UI text (translated) rather than evidence text]
 const rows:[string,string,boolean][]=[
 [t("guide.model.parameters"),m.size,false],[t("guide.model.builtFrom"),m.base,false],[t("guide.model.availability"),m.weights,false],
 [t("guide.model.repositoryCreated"),m.repository_created||t("guide.model.notVerified"),!m.repository_created],
 [t("guide.model.gpuMemory"),m.loaded_gpu_gib==null?t("guide.model.notRecorded"):t("guide.model.gib",{n:fmt.number(m.loaded_gpu_gib,2)}),true],
 [t("guide.model.precision"),m.precision,false],[t("guide.model.context"),m.context,false],[t("guide.model.choiceLimit"),m.options,false],
 [t("guide.model.loadTime"),m.load_seconds==null?t("guide.model.notApplicableOrRecorded"):t("guide.model.seconds",{n:fmt.number(m.load_seconds,2)}),true]
 ];
 return <><div className="results-select">{catalog.models.map(x=><button key={x.id} className={x.id===m.id?"selected":""} onClick={()=>onSelect(x.id)}>{x.name}</button>)}</div><section className="model-guide"><EnglishOnly>
 <div className="section-title"><div><span className="eyebrow">{m.kind}</span><h2>{m.name}</h2><p>{m.note}</p></div>{m.url&&<a lang={lang} className="button secondary" href={m.url} target="_blank" rel="noreferrer">{t("guide.model.officialSource")}</a>}</div>
 <dl className="profile-grid">{rows.map(([k,v,ui])=><div key={k}><dt lang={lang}>{k}</dt><dd lang={ui?lang:undefined}>{v}</dd></div>)}</dl>
 <p className="small muted">{m.memory_note} {modelProse.memory}</p><p className="small muted">{m.date_note} {modelProse.dates(catalog.checked)}</p><details className="explain"><summary lang={lang}>{t("guide.model.exactVersion")}</summary><code>{m.revision}</code></details></EnglishOnly></section></>
}
function sourceRows(t:TFunction):[string,number,string,string,string][]{
 return [
 [t("packs.jevbench-public"),231,t("guide.sources.keys.publicKey"),t("guide.sources.tests.jevbench"),"https://github.com/fstandhartinger/jevbench"],
 [t("packs.typed-decisions"),2000,t("guide.sources.keys.aiReference"),t("guide.sources.tests.typed"),"https://huggingface.co/datasets/LocalLLaMA/typed-decisions"],
 [t("packs.classification"),1500,t("guide.sources.keys.publicKeys"),t("guide.sources.tests.classification"),"https://huggingface.co/datasets/legacy-datasets/banking77"],
 [t("packs.multilingual"),1000,t("guide.sources.keys.publicKeys"),t("guide.sources.tests.multilingual"),"https://huggingface.co/datasets/facebook/xnli"],
 [t("guide.sources.groups.relevance"),500,t("guide.sources.keys.relevanceLabels"),t("guide.sources.tests.relevance"),"https://huggingface.co/datasets/BeIR/scifact"],
 [t("guide.sources.groups.policy"),1440,t("guide.sources.keys.ruleDerived"),t("guide.sources.tests.policy"),""],
 [t("explore.types.robustness"),1000,t("guide.sources.keys.ruleDerived"),t("guide.sources.tests.changed"),""]
 ];
}
export function SourcesGuide(){
 const { t, i18n } = useTranslation(); const lang = i18n.language; const fmt = useFormat();
 const glossary:[string,string][]=[
 [t("guide.glossary.accuracy.term"),t("guide.glossary.accuracy.definition")],
 [t("guide.glossary.strict.term"),t("guide.glossary.strict.definition")],
 [t("guide.glossary.matched.term"),t("guide.glossary.matched.definition")],
 [t("guide.glossary.p50.term"),t("guide.glossary.p50.definition")],
 [t("guide.glossary.coverage.term"),t("guide.glossary.coverage.definition")],
 [t("guide.glossary.teacher.term"),t("guide.glossary.teacher.definition")],
 [t("guide.glossary.perturbations.term"),t("guide.glossary.perturbations.definition")],
 [t("guide.glossary.reliability.term"),t("guide.glossary.reliability.definition")]
 ];
 return <section className="sources-guide"><h2>{t("guide.sources.title",{n:fmt.number(7671)})}</h2><EnglishOnly><p>{sourcesProse.intro}</p>
 <div className="table-scroll" lang={lang}><table><thead><tr><th>{t("guide.sources.table.group")}</th><th>{t("guide.sources.table.cases")}</th><th>{t("guide.sources.table.answerSource")}</th><th>{t("guide.sources.table.tests")}</th></tr></thead><tbody>{sourceRows(t).map(([name,n,key,desc,url])=><tr key={name}><td>{url?<a href={url} target="_blank" rel="noreferrer">{name}{externalMark}</a>:name}</td><td>{fmt.number(n)}</td><td>{key}</td><td>{desc}</td></tr>)}</tbody></table></div>
 <p className="small muted">{sourcesProse.additionalLead} {extraSources.map(([name,url],i)=><Fragment key={name}>{i>0&&" · "}<a href={url} target="_blank" rel="noreferrer">{name}</a></Fragment>)}{sourcesProse.additionalTail}</p>
 <h2 lang={lang}>{t("guide.sources.answerKeyTitle")}</h2><p>{sourcesProse.answerKey}</p><p>{sourcesProse.astra}</p>
 <h2 lang={lang}>{t("guide.sources.abcdTitle")}</h2><p>{sourcesProse.abcd}</p></EnglishOnly>
 <h2>{t("guide.sources.glossaryTitle")}</h2><dl className="glossary">{glossary.map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
 </section>
}
function Value({value}:{value:unknown}){
 if(Array.isArray(value))return <ul>{value.map((v,i)=><li key={i}><Value value={v}/></li>)}</ul>;
 if(value!==null&&typeof value==="object")return <dl>{Object.entries(value).map(([k,v])=><div key={k}><dt>{k.replaceAll("_"," ")}</dt><dd><Value value={v}/></dd></div>)}</dl>;
 return <span>{String(value)}</span>
}
export function CaseState({text}:{text:string}){
 const { t, i18n } = useTranslation(); const lang = i18n.language;
 let parsed:unknown=null;try{parsed=JSON.parse(text)}catch{/* Text state. */}
 const parts=text.split(/(?=(?:Policy|Rubric|Claim|Document title|Document|Premise|Hypothesis|Proposed answer|Available tools|Source record|Query):)/g);
 return <div className="structured-state"><div className="field-label">{t("guide.caseState.label")}</div><EnglishOnly><p className="small muted">{caseStateProse}</p>
 {parsed!==null&&typeof parsed==="object"?<Value value={parsed}/>:parts.filter(Boolean).map((s,i)=>{const m=s.match(/^([^:\n]{1,30}):\s*([\s\S]*)$/);return <section key={i}>{m?<h4>{m[1]}</h4>:<h4 lang={lang}>{parts.length>1?t("guide.caseState.situation"):t("guide.caseState.inputText")}</h4>}<p>{m?m[2]:s}</p></section>})}</EnglishOnly>
 <details className="explain"><summary>{t("guide.caseState.exactInput")}</summary><pre>{text}</pre></details></div>
}
function taskName(t:TFunction,k:string){
 const names:Record<string,string>={"JevBench public":t("packs.jevbench-public"),"SST-2":t("explore.types.sst-2"),"AG News":t("explore.types.ag-news"),"XNLI":t("guide.breakdown.xnli"),"SciFact":t("explore.types.scifact"),"Arena Fresh":t("explore.types.arena-fresh"),"Robustness":t("explore.types.robustness")};
 return names[k]||k;
}
export function TaskBreakdown(){
 const { t, i18n } = useTranslation(); const lang = i18n.language; const fmt = useFormat();
 const pct=(v:number|null|undefined)=>v==null?t("common.unavailable"):fmt.percent(v,2);
 return <section className="analysis-panel"><h2>{t("guide.breakdown.title")}</h2><EnglishOnly><p>{breakdownProse.intro}</p><div className="table-scroll" lang={lang}><table><thead><tr><th>{t("guide.breakdown.task")}</th><th>{t("guide.breakdown.questions")}</th>{["jev","winnow","decider","nimble","plumb","laya"].map(id=><th key={id}>{catalog.models.find(x=>x.id===id)?.name}</th>)}</tr></thead><tbody>{Object.entries(taskData.groups).map(([k,g])=><tr key={k}><td>{taskName(t,k)}</td><td>{fmt.number(g.n)}</td>{["jev","winnow","decider","nimble","plumb","laya"].map(id=><td key={id}>{pct((g.scores as Record<string,number>)[id])}</td>)}</tr>)}</tbody></table></div><p className="small muted">{breakdownProse.footnote}</p></EnglishOnly></section>
}
export function ABCDResults(){
 const { t, i18n } = useTranslation(); const lang = i18n.language; const fmt = useFormat();
 const [condition,setCondition]=useViewState("abcd:condition","full_handbook"),[task,setTask]=useViewState("abcd:task","combined"),[metric,setMetric]=useViewState("abcd:metric","label"),[model,setModel]=useViewState("abcd:model","");
 const models=abcd.models as unknown as Record<string,{natural:Record<string,Record<string,number|null>>;combined:Record<string,Record<string,number|null>>}>;
 const rows=Object.entries(models).filter(([id])=>!model||id===model).map(([id,m])=>{const x=task==="combined"?m.combined[condition]:m.natural[condition+"/"+task];return {id,x}});
 const insights:[string,string][]=[[t("guide.abcd.rankingTitle"),abcdProse.ranking],[t("guide.abcd.speedTitle"),abcdProse.speed],[t("guide.abcd.noWinnerTitle"),abcdProse.noWinner]];
 return <section><h2>{t("guide.abcd.title")}</h2><EnglishOnly><p>{abcdProse.intro}</p>
 <div className="abcd-controls" lang={lang}><label>{t("abcd.filters.policyInput")}<select value={condition} onChange={e=>setCondition(e.target.value)}><option value="full_handbook">{t("abcd.filters.fullHandbook")}</option><option value="retrieved_policy">{t("abcd.filters.retrievedPolicy")}</option></select></label><label>{t("guide.abcd.task")}<select value={task} onChange={e=>setTask(e.target.value)}><option value="combined">{t("guide.abcd.tasks.combined")}</option><option value="action">{t("guide.abcd.tasks.action")}</option><option value="route">{t("guide.abcd.tasks.route")}</option></select></label><label>{t("abcd.table.model")}<select value={model} onChange={e=>setModel(e.target.value)}><option value="">{t("guide.abcd.compareAll",{n:fmt.number(Object.keys(models).length)})}</option>{Object.keys(models).map(id=><option key={id} value={id}>{catalog.models.find(m=>m.id===id)?.name||id}</option>)}</select></label><label>{t("explore.analysis.score")}<select value={metric} onChange={e=>setMetric(e.target.value)}><option value="label">{t("explore.analysis.metrics.label")}</option><option value="strict">{t("explore.analysis.metrics.strict")}</option></select></label></div>
 <p className="score-note">{task==="action"?abcdProse.actionNote:abcdProse.combinedNote}</p>
 <div className="table-scroll" lang={lang}><table className="task-ranking"><thead><tr><th>{t("abcd.table.model")}</th><th>{t("guide.abcd.referenceAgreement")}</th><th>{t("explore.table.matchesScored")}</th><th>{t("explore.table.nonMatches")}</th><th>{t("guide.abcd.coverage")}</th></tr></thead><tbody>{rows.sort((a,b)=>Number(b.x[metric+"_accuracy_supported"]??-1)-Number(a.x[metric+"_accuracy_supported"]??-1)).map(({id,x},i)=>{
 const supported=Number(x.supported??0),correct=Number(x[metric+"_correct"]??0),value=x[metric+"_accuracy_supported"];
 return <tr key={id} className={i===0&&value!=null&&!model?"leading-row":""}><td>{catalog.models.find(m=>m.id===id)?.name||id}</td><td><strong>{value==null?t("explore.unsupported"):fmt.percent(value,2)}</strong>{value!=null&&<span className="table-bar"><i style={{width:(value*100)+"%"}}/></span>}{id==="nimble"&&condition==="full_handbook"&&<small>{t("guide.abcd.exceedsLimit")}</small>}</td><td>{supported?`${fmt.number(correct)} / ${fmt.number(supported)}`:"—"}</td><td>{supported?fmt.number(supported-correct):"—"}</td><td>{t("guide.abcd.supported",{supported:fmt.number(supported),planned:fmt.number(Number(x.planned??0))})}<small>{t("guide.abcd.unsupportedCount",{n:fmt.number(Number(x.unsupported??0))})}</small></td></tr>;
 })}</tbody></table></div><p className="small muted">{abcdProse.footnote}</p>
 <div className="takeaway-list">{insights.map(([title,prose])=><article key={title}><b>→</b><div><h3 lang={lang}>{title}</h3><p>{prose}</p></div></article>)}</div>
 <details className="explain"><summary lang={lang}>{t("guide.abcd.scopeTitle")}</summary><p>{abcdProse.scope}</p></details></EnglishOnly></section>
}

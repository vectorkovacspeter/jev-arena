"""Two deterministic simulated workflows. No real-world actions or external tools."""
import random
from collections import deque
from arena.contracts import Case,Question
from arena.i18n.prompts import labels,prompt

# Every episode string comes from locales/<lang>/prompts.yaml. The simulation itself works on stable
# English ids; localized answers are mapped back through the case's label->id map before they act.
# English cases, traces and result rows are byte-identical to the pre-i18n output: the "<lang>:" id
# prefix, provenance["label_ids"], trace["answer_id"] and row["language"] appear only for lang!="en".
def localize(lang,group,ids):
    names=labels(lang,group);shown=[names[x] for x in ids]
    return shown,dict(zip(shown,ids))

def localized_extras(lang,label_ids):
    return {} if lang=='en' else {'provenance':{'label_ids':dict(label_ids)}}

def answer_id_field(lang,answer_id):
    return {} if lang=='en' else {'answer_id':answer_id}

def distance(start,goal,blocked,size=6):
    queue=deque([(start,0)]);seen={start}
    while queue:
        (x,y),d=queue.popleft()
        if (x,y)==goal:return d
        for dx,dy in ((0,-1),(1,0),(0,1),(-1,0)):
            p=(x+dx,y+dy)
            if p not in seen and p not in blocked and 0<=p[0]<size and 0<=p[1]<size:seen.add(p);queue.append((p,d+1))
    return 999

class Warehouse:
    def __init__(self,seed,lang='en'):
        self.seed=seed;self.lang=lang;self.prefix='' if lang=='en' else f'{lang}:';self.label_ids={};self.pos=(0,0);self.goal=(5,5);rng=random.Random(seed)
        self.blocked=set(rng.sample([(x,y) for x in range(1,5) for y in range(1,5)],5));self.steps=0;self.violations=0;self.trace=[]
    def case(self):
        ids=['north','east','south','west'];directions=[(0,-1),(1,0),(0,1),(-1,0)];scores=[]
        shown,self.label_ids=localize(self.lang,'directions',ids)
        for dx,dy in directions:
            pos=(self.pos[0]+dx,self.pos[1]+dy)
            scores.append(distance(pos,self.goal,self.blocked) if 0<=pos[0]<6 and 0<=pos[1]<6 and pos not in self.blocked else 999)
        gold=shown[scores.index(min(scores))]
        state=prompt(self.lang,'episodes.warehouse_state',pos=self.pos,goal=self.goal,blocked=sorted(self.blocked))
        return Case(id=f'{self.prefix}warehouse-{self.seed}-{self.steps}',cluster=f'{self.prefix}warehouse-{self.seed}',pack='Episodes',family='Warehouse',state=state,question=Question(id='move',kind='choice',text=prompt(self.lang,'episodes.warehouse_question'),labels=shown),gold=gold,acceptable=[shown[i] for i,v in enumerate(scores) if v==min(scores)],language=self.lang,**localized_extras(self.lang,self.label_ids))
    def step(self,p):
        before=self.pos;directions={'north':(0,-1),'east':(1,0),'south':(0,1),'west':(-1,0)}
        answer_id=self.label_ids.get(p.selected) if p.selected is not None else None
        dx,dy=directions.get(answer_id,(0,0));after=(before[0]+dx,before[1]+dy)
        valid=p.status=='ok' and after not in self.blocked and 0<=after[0]<6 and 0<=after[1]<6
        if valid:self.pos=after
        else:self.violations+=1
        self.trace.append({'step':self.steps,'before':before,'after':self.pos,'answer':p.selected,**answer_id_field(self.lang,answer_id),'status':p.status,'request_ms':p.request_ms,'valid':valid});self.steps+=1
    @property
    def done(self):return self.pos==self.goal or self.steps>=40
    def result(self):
        row={'task':'warehouse','seed':self.seed,'success':self.pos==self.goal,'steps':self.steps,'violations':self.violations,'reward':int(self.pos==self.goal)*100-self.steps-self.violations*5,'blocked':sorted(self.blocked),'goal':self.goal,'trace':self.trace}
        if self.lang!='en':row['language']=self.lang
        return row

class Tickets:
    def __init__(self,seed,lang='en'):
        self.seed=seed;self.lang=lang;self.prefix='' if lang=='en' else f'{lang}:';self.label_ids={}
        self.rng=random.Random(seed);self.steps=0;self.violations=0;self.correct=0;self.trace=[];self.current=None
    def case(self):
        topic=self.rng.choice(['payment','service outage','onboarding']);queue={'payment':'Billing','service outage':'Engineering','onboarding':'Success'}[topic];restricted=self.rng.random()<.25
        gold='Review' if restricted else queue
        # current (and so the trace) keeps the stable English ids for topic and gold in every language.
        self.current={'topic':topic,'restricted':restricted,'gold':gold}
        shown,self.label_ids=localize(self.lang,'ticket_queues',['Billing','Engineering','Success','Review'])
        names=dict(zip(self.label_ids.values(),self.label_ids))
        state=prompt(self.lang,'episodes.tickets_state',seed=self.seed,step=self.steps,topic=prompt(self.lang,f'episodes.ticket_topics.{topic}'),restricted=prompt(self.lang,'fresh.yes' if restricted else 'fresh.no'))
        return Case(id=f'{self.prefix}tickets-{self.seed}-{self.steps}',cluster=f'{self.prefix}tickets-{self.seed}',pack='Episodes',family='Ticket workflow',state=state,question=Question(id='route',kind='choice',text=prompt(self.lang,'episodes.tickets_question'),labels=shown),gold=names[gold],language=self.lang,**localized_extras(self.lang,self.label_ids))
    def step(self,p):
        answer_id=self.label_ids.get(p.selected) if p.selected is not None else None
        good=p.status=='ok' and answer_id==self.current['gold'];self.correct+=good
        self.violations+=self.current['restricted'] and answer_id!='Review'
        self.trace.append({'step':self.steps,**self.current,'answer':p.selected,**answer_id_field(self.lang,answer_id),'correct':good,'request_ms':p.request_ms});self.steps+=1
    @property
    def done(self):return self.steps>=12
    def result(self):
        row={'task':'tickets','seed':self.seed,'success':self.correct==12,'steps':self.steps,'violations':self.violations,'reward':self.correct*10-self.violations*20,'trace':self.trace}
        if self.lang!='en':row['language']=self.lang
        return row

async def run_episodes(adapter,count,paid_cap,deadline_ms=None,on_progress=None,lang='en'):
    records=[]
    for cls in (Tickets,Warehouse):
        for seed in range(count//2):
            env=cls(5090+seed,lang=lang)
            while not env.done:
                pred=await adapter.predict(env.case(),paid_cap)
                missed=deadline_ms is not None and pred.request_ms>deadline_ms
                applied=pred.model_copy(update={'status':'timeout','selected':None}) if missed else pred
                env.step(applied);env.trace[-1]['deadline_missed']=missed
                env.trace[-1]['late_answer']=pred.selected if missed else None
            row=env.result();row['model_id']=adapter.id;row['mode']='deadline_500ms' if deadline_ms else 'untimed_quality';row['wall_request_ms']=sum(t['request_ms'] for t in row['trace']);row['deadline_ms']=deadline_ms;row['deadline_misses']=sum(t['deadline_missed'] for t in row['trace']) if deadline_ms else None
            records.append(row)
            if on_progress:on_progress(row)
    return records

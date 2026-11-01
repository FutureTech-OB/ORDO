const $ = id => document.getElementById(id);
const colors = ['#187b6c', '#a9b9a1', '#bd7a35', '#6c79a8'];
const policyNames = {g0_p0:'No guidance | No penalty',g0_p10:'No guidance | High penalty',g1_p0:'Exploration guidance | No penalty',g1_p10:'Exploration guidance | High penalty'};
let archive, current, history = [];
const number = (n,d=1) => Number(n).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d});
function showTab(name){document.querySelectorAll('.tab').forEach(b=>{b.classList.toggle('active',b.dataset.tab===name);b.setAttribute('aria-selected',b.dataset.tab===name);});document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('hidden',p.id!==name));}
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>showTab(b.dataset.tab)));
$('open-experiment').addEventListener('click',()=>showTab('experiment'));
function download(name,value,mime='application/json'){const url=URL.createObjectURL(new Blob([typeof value==='string'?value:JSON.stringify(value,null,2)],{type:mime}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
function kpi(target,items){$(target).replaceChildren(...items.map(([label,value,sub])=>{let el=document.createElement('div');el.className='kpi';[['kpi-label',label],['kpi-value',value],['kpi-sub',sub]].forEach(([cl,t])=>{let x=document.createElement('div');x.className=cl;x.textContent=t;el.append(x)});return el;}));}
const ns='http://www.w3.org/2000/svg';
function svgEl(tag,attrs={},text){const e=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;return e;}
function chart(target,series,{max=100,min=0,suffix=''}={}){const w=600,h=260,left=43,right=15,top=16,bottom=33;let svg=svgEl('svg',{viewBox:`0 0 ${w} ${h}`,role:'img','aria-label':target.includes('exploration')?'Exploration rate by round and condition':'Performance by round and condition'});const count=Math.max(...series.map(s=>s.values.length));const X=i=>left+i/(Math.max(count-1,1))*(w-left-right);const Y=v=>h-bottom-(v-min)/(max-min)*(h-top-bottom);for(let i=0;i<=4;i++){let value=min+(max-min)*i/4,y=Y(value);svg.append(svgEl('line',{x1:left,y1:y,x2:w-right,y2:y,stroke:'#e9eee6','stroke-dasharray':'3 4'}));svg.append(svgEl('text',{x:left-10,y:y+3,'text-anchor':'end'},Math.round(value)+suffix));}for(let i=0;i<count;i++){if(i===0||i===count-1||(i+1)%Math.max(2,Math.floor(count/5))===0)svg.append(svgEl('text',{x:X(i),y:h-10,'text-anchor':'middle'},i+1));}series.forEach((s,j)=>{svg.append(svgEl('polyline',{points:s.values.map((v,i)=>`${X(i)},${Y(v)}`).join(' '),fill:'none',stroke:s.color||colors[j%4],'stroke-width':2.6,'stroke-linejoin':'round','stroke-linecap':'round'}));let last=s.values.length-1;svg.append(svgEl('circle',{cx:X(last),cy:Y(s.values[last]),r:3.6,fill:s.color||colors[j%4]}));});$(target).replaceChildren(svg);}
function legend(target,series){$(target).replaceChildren(...series.map((s,i)=>{const item=document.createElement('span');item.className='legend-item';const svg=svgEl('svg',{width:15,height:4});svg.append(svgEl('line',{x1:0,y1:2,x2:15,y2:2,stroke:s.color||colors[i%4],'stroke-width':3}));item.append(svg,document.createTextNode(s.name));return item;}));}
function archiveSeries(metric,multiplier=1){return Object.keys(policyNames).map((id,i)=>{const worlds=archive.worlds.filter(w=>w.policy.id===id);return {name:policyNames[id],color:colors[i],values:worlds[0].metrics.map((_,r)=>worlds.reduce((s,w)=>s+w.metrics[r][metric],0)/worlds.length*multiplier)};});}
async function loadArchive(){try{const res=await fetch('/api/archive');if(!res.ok)throw Error('Could not load archive data');archive=await res.json();const u=archive.summary.usage;kpi('archive-kpis',[['Fresh decisions',number(archive.summary.audit.fresh_decisions,0),'A new judgment for each member and round'],['Simulation worlds','12','Four policy conditions x three paired seeds'],['Recorded input cost','$'+number(u.observed_input_cost_usd,2),'Computed from returned usage'],['Active execution time',number(u.active_execution_s/60,2)+' min','Completed execution periods']]);const explore=archiveSeries('explore_share',100);chart('exploration-chart',explore,{max:60,suffix:''});chart('performance-chart',archiveSeries('gross_performance'));legend('archive-legend',explore);const rows=Object.keys(policyNames).map(id=>{const ws=archive.summary.worlds.filter(w=>w.policy===id);const avg=k=>ws.reduce((s,w)=>s+w[k],0)/ws.length;const tr=document.createElement('tr');[policyNames[id],number(avg('mean_exploration')*100)+'%',number(avg('final_gross'),2),number(avg('cumulative_net'),2)].forEach(v=>{let td=document.createElement('td');td.textContent=v;tr.append(td)});return tr;});$('archive-table').replaceChildren(...rows);}catch(e){error(e.message);}}
function error(text){$('error').textContent=text;$('error').classList.remove('hidden');}
$('export-archive').addEventListener('click',()=>archive&&download('orgabm-archived-jev-pilot.json',archive));
function config(){const c={};['agents','departments','rounds','seed','penalty','approval_gain','intervention_round'].forEach(k=>c[k]=Number($(k).value));['guidance','anonymous'].forEach(k=>c[k]=$(k).checked);['contact','engine'].forEach(k=>c[k]=$(k).value);
  if($('persona-enabled').checked)c.population={records:readObject('persona-records',true),sampling:$('persona-sampling').value,seed:Number($('persona-seed').value)};
  if($('structure-template').value!=='none')c.structure={...readObject('structure-options'),template:$('structure-template').value};
  return {...c,batch_size:64,concurrency:4};}
$('export-config').addEventListener('click',()=>{try{download('organization-experiment.json',config());}catch(e){error(e.message);}});
document.querySelectorAll('[data-preset]').forEach(b=>b.addEventListener('click',()=>{const kind=b.dataset.preset;$('contact').value=kind==='approval'?'mixed':kind;$('approval_gain').value=kind==='approval'?10:0;$('penalty').value=0;$('intervention_round').value=kind==='approval'?Math.min(6,Number($('rounds').value)):1;$('guidance').checked=false;}));
$('run-form').addEventListener('submit',async e=>{e.preventDefault();$('error').classList.add('hidden');const button=$('run-button');button.disabled=true;button.textContent='Running…';try{const res=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(config())});const data=await res.json();if(!res.ok)throw Error(data.error||'Execution failed');current=data;history.push(data);history=history.slice(-2);renderRun();}catch(err){error(err.message);}finally{button.disabled=false;button.textContent='Run rule experiment →';}});
function runName(r,i){return `${i+1}. ${r.config.contact} / Threshold ${r.config.approval_gain} / ${r.config.engine}`;}
function renderRun(){const r=current,last=r.metrics.at(-1);$('run-empty').classList.add('hidden');$('run-results').classList.remove('hidden');$('run-status').textContent=`Complete | ${number(r.decisions,0)} rule choices | ${number(r.elapsed_s,2)} s`;$('run-description').textContent=`N=${r.config.agents} · seed=${r.config.seed}`;kpi('run-kpis',[['Final-round performance',number(last.gross_performance,2),'Before penalties'],['Cumulative net payoff',number(last.cumulative_net,1),'Per member, after penalties'],['Remaining methods',number(last.unique_solutions,0),'Organization-wide'],['Adoption denials',number(r.metrics.reduce((s,m)=>s+m.approval_denials,0),0),'Across all rounds']]);const series=history.map((x,i)=>({name:runName(x,i),values:x.metrics.map(m=>m.gross_performance),color:colors[i===history.length-1?0:2]}));chart('run-chart',series);legend('run-legend',series);let note='Rules use explicit choice functions; the simulator enforces role rights and contact boundaries.';if(history.length===2){const [a,b]=history;const matched=a.initial_state_sha256===b.initial_state_sha256&&a.landscape_sha256===b.landscape_sha256&&a.population_sha256===b.population_sha256;note=(matched?'The runs share population, initial methods, and task environment.':'These runs have different initial conditions.')+' '+note;} $('comparison').textContent=note;$('trace-round').max=r.config.rounds;$('trace-round').value=1;renderTrace();network(r.snapshots.at(-1));}
function renderTrace(){if(!current)return;const t=Number($('trace-round').value),a=Number($('trace-agent').value);$('trace-round-label').textContent=t;const trace=current.traces.find(x=>x.round===t&&x.agent===a);$('trace-summary').replaceChildren();const values=[['Proposed action',trace.requested_action],['Executed action',trace.feedback.action],['Approval denied',trace.feedback.approval_denied?'Yes':'No'],['Performance improvement',number(trace.feedback.gain,3)],['Round net payoff',number(trace.feedback.net,3)]];values.forEach(([k,v])=>{let p=document.createElement('div');p.textContent=`${k}：${v}`;$('trace-summary').append(p)});$('trace-json').textContent=JSON.stringify({observation:trace.observation,probabilities:trace.probabilities},null,2);}
$('trace-round').addEventListener('input',renderTrace);$('trace-agent').addEventListener('change',renderTrace);
function network(snapshot){const svg=svgEl('svg',{viewBox:'0 0 360 245',role:'img','aria-label':'Departments and final-round contact network'});const departments=[...new Set(snapshot.nodes.map(n=>n.department))].sort((a,b)=>a-b);let positions={};departments.forEach((d,k)=>{const group=snapshot.nodes.filter(n=>n.department===d);const angle=k/departments.length*Math.PI*2-Math.PI/2;const cx=180+Math.cos(angle)*(departments.length>1?95:0),cy=120+Math.sin(angle)*(departments.length>1?75:0);svg.append(svgEl('text',{x:cx,y:cy+49,'text-anchor':'middle',fill:'#6b7f72','font-size':10},`D${d+1}`));group.forEach((n,j)=>{const q=j/group.length*Math.PI*2;positions[n.id]=[cx+Math.cos(q)*(18+Math.floor(j/16)*9),cy+Math.sin(q)*(18+Math.floor(j/16)*9)];});});snapshot.edges.forEach(([a,b])=>{if(positions[a]&&positions[b])svg.append(svgEl('line',{x1:positions[a][0],y1:positions[a][1],x2:positions[b][0],y2:positions[b][1],stroke:'#b7c8bb','stroke-width':.6,opacity:.4}));});snapshot.nodes.forEach(n=>{const el=svgEl('circle',{cx:positions[n.id][0],cy:positions[n.id][1],r:3.3,fill:colors[n.department%4],stroke:'white','stroke-width':.8});el.append(svgEl('title',{},`Employee ${n.id} | D${n.department+1} | Performance ${number(n.performance,1)}`));svg.append(el);});$('network').replaceChildren(svg);}
$('export-run').addEventListener('click',()=>current&&download(`orgabm-${current.config.engine}-${current.config.seed}.json`,current));
loadArchive();

function readObject(id, array=false){
  let value;
  try{value=JSON.parse($(id).value);}catch{throw Error(`${$(id).closest('label').firstChild.textContent.trim()}: Invalid JSON`);}
  if(array?!Array.isArray(value):!value||typeof value!=='object'||Array.isArray(value))throw Error(array?'Persona records must be a JSON array':'Organization settings must be a JSON object');
  return value;
}
async function postJSON(path, body){
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await response.json();if(!response.ok)throw Error(data.error||'Request failed');return data;
}
async function personaAction(button, task){
  button.disabled=true;$('error').classList.add('hidden');
  try{await task();}catch(e){error(e.message);$('persona-status').textContent='Incomplete: '+e.message;}finally{button.disabled=false;}
}
$('persona-import').addEventListener('click',e=>personaAction(e.currentTarget,async()=>{
  const file=$('persona-file').files[0];if(!file)throw Error('Select a local data file first');
  if(file.size>1000000)throw Error('Select a subset of at most 1 MB; import larger files through Python');
  const body={text:await file.text(),format:file.name.split('.').at(-1).toLowerCase(),preset:$('persona-preset').value};
  if($('persona-map').value.trim())body.field_map=readObject('persona-map');
  const data=await postJSON('/api/personas/import',body);
  $('persona-records').value=JSON.stringify(data.records,null,2);$('persona-enabled').checked=true;
  $('persona-status').textContent=`Imported ${data.count} Personas. Choose an assignment method and preview the population.`;
  $('workforce-result').classList.add('hidden');
}));
$('persona-example').addEventListener('click',e=>personaAction(e.currentTarget,async()=>{
  const response=await fetch('/api/persona-example');if(!response.ok)throw Error('Could not load the Persona example');const c=await response.json();
  ['agents','departments','rounds','seed','contact','engine'].forEach(k=>$(k).value=c[k]);
  ['penalty','approval_gain'].forEach(k=>$(k).value=0);$('intervention_round').value=1;
  ['guidance','anonymous'].forEach(k=>$(k).checked=false);
  $('persona-enabled').checked=true;$('persona-records').value=JSON.stringify(c.population.records,null,2);
  $('persona-sampling').value=c.population.sampling;$('persona-seed').value=c.population.seed;
  $('structure-template').value=c.structure.template;$('structure-options').value='{}';
  $('persona-status').textContent='Loaded four fictional Personas for sampling sixteen independent members with replacement.';
  $('workforce-result').classList.add('hidden');
}));
$('workforce-preview').addEventListener('click',e=>personaAction(e.currentTarget,async()=>{
  const data=await postJSON('/api/workforce/preview',config());
  $('workforce-rows').replaceChildren(...data.preview.map(row=>{
    const tr=document.createElement('tr');
    const probability=row.persona?.source?.orgabm_assignment?.probability;
    [row.agent,row.persona?.id??'—',row.persona?.name||'—',`D${row.department+1}`,row.role_definition.title,row.manager??'—',typeof probability==='number'?number(probability*100,1)+'%':'—'].forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td);});return tr;
  }));
  $('workforce-result').classList.remove('hidden');
  $('persona-status').textContent=`Valid configuration: ${data.population_size} members, ${data.distinct_personas} Personas. Population ID ${data.population_sha256.slice(0,12)}.`;
}));
for(const id of ['persona-enabled','persona-records','persona-sampling','persona-seed','structure-template','structure-options','agents','departments','seed']){
  $(id).addEventListener('input',()=>{$('workforce-result').classList.add('hidden');$('persona-status').textContent='Configuration changed. Preview again.';});
}

function applyAssignmentConfig(c){
  for(const key of ['agents','departments','rounds','seed','penalty','approval_gain','intervention_round','contact','engine'])if(c[key]!==undefined)$(key).value=c[key];
  for(const key of ['guidance','anonymous'])$(key).checked=!!c[key];
  $('persona-enabled').checked=true;$('persona-records').value=JSON.stringify(c.population.records,null,2);
  $('persona-sampling').value=c.population.sampling||'without_replacement';$('persona-seed').value=c.population.seed??2026;
  $('structure-template').value=c.structure?.template||'none';
  const options={...(c.structure||{})};delete options.template;$('structure-options').value=JSON.stringify(options,null,2);
  $('workforce-result').classList.add('hidden');
}
$('assignment-mode').addEventListener('change',()=>{$('assignment-threshold').disabled=$('assignment-mode').value==='pool';});
$('assignment-example').addEventListener('click',e=>personaAction(e.currentTarget,async()=>{
  const response=await fetch('/api/assignment-example');if(!response.ok)throw Error('Could not load the position-assignment example');
  const job=await response.json();applyAssignmentConfig(job.config);
  $('assignment-mode').value=job.mode;$('assignment-threshold').value=job.threshold;$('assignment-threshold').disabled=false;
  $('assignment-seed').value=job.seed;$('assignment-context').value=job.context;$('assignment-limit').value='';
  $('persona-status').textContent='Loaded 24 fictional candidates for two manager and six employee positions. Local preview.';
}));
$('assignment-preview').addEventListener('click',e=>personaAction(e.currentTarget,async()=>{
  if(!$('persona-enabled').checked)throw Error('Import or enter a Persona candidate pool first');
  const job={config:config(),mode:$('assignment-mode').value,threshold:Number($('assignment-threshold').value),seed:Number($('assignment-seed').value),batch_size:64,context:$('assignment-context').value};
  if($('assignment-limit').value.trim())job.max_evaluations=Number($('assignment-limit').value);
  const preview=await postJSON('/api/personas/assignment-preview',job);
  $('assignment-status').textContent=`${preview.pool_size} candidates → ${preview.slots} positions; ${Object.values(preview.roles).map(r=>r.title+' '+r.count+' members').join(', ')}. Up to ${preview.max_evaluations} evaluations and ${preview.max_provider_requests} native requests. Local preview.`;
  download('persona-assignment-job.json',job);
}));
$('assignment-import').addEventListener('click',e=>personaAction(e.currentTarget,async()=>{
  const file=$('assignment-result-file').files[0];if(!file)throw Error('Select a completed assignment or configuration');
  if(file.size>1000000)throw Error('Select config.json up to 1 MB; inspect the full audit locally');
  const raw=JSON.parse(await file.text());
  if('status' in raw&&raw.status!=='complete')throw Error('The assignment still has unfilled positions');
  const c=raw.config||raw;
  if(!c.population||c.population.sampling!=='ordered'||c.structure?.template!=='custom')throw Error('The assignment must specify fixed people and position mappings');
  await postJSON('/api/workforce/preview',c);
  applyAssignmentConfig(c);
  $('persona-status').textContent='Applied the completed population and positions. Preview and run the experiment.';
  $('assignment-status').textContent='Imported the fixed workforce; assignment probabilities and provenance remain in Persona source records.';
}));

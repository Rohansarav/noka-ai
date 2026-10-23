/** Disposable browser QA. --providers spends bounded Tavily/OpenAI calls; no user profile is touched. */
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const base=process.env.NOKA_TEST_URL||'http://127.0.0.1:8000';
const out=path.resolve('docs/qa/pathway-research');
const providers=process.argv.includes('--providers');
const proposalFixture=process.argv.includes('--proposal-fixture');

(async()=>{
  fs.mkdirSync(out,{recursive:true});
  const browser=await chromium.launch({headless:true,channel:'msedge'});
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.name+': '+e.message));
  const headers={'X-Noka-CSRF':'1',Origin:base};
  let pid;
  const report={fixture:'Disposable demo profile; no real user data or human review.',checks:[],provider_test:providers};
  async function api(url,method='GET',data){
    const r=await context.request.fetch(base+url,{method,data,headers});
    if(!r.ok())throw Error(`${method} ${url}: ${r.status()}`);
    return r.status()===204?null:r.json();
  }
  async function waitRun(id){
    for(let i=0;i<100;i++){
      const r=(await api('/api/pathway-research?role_id=15-1252.00')).runs.find(r=>r.id===id);
      if(r&&!['queued','searching','extracting','analyzing','planning'].includes(r.status))return r;
      await new Promise(r=>setTimeout(r,2000));
    }
    throw Error('Research did not settle within QA deadline');
  }
  try{
    pid=(await api('/api/profiles','POST',{is_demo:true})).id;
    const skills=[{skill_id:'2.A.2.a',level:'strong',years:null},{skill_id:'2.B.3.e',level:'working',years:null},{skill_id:'2.A.1.e',level:'working',years:null}];
    await api(`/api/profiles/${pid}/skills`,'PUT',{skills,country:'MY',interests:['15-1252.00'],onboarding:{current_field:'Software engineering — QA fixture',interests:['15-1252.00'],skills,projects:'QA fixture: a small local Python service with basic tests.',constraints:'QA fixture: use public data and validate access to a reviewer.',aspirations:[{title:'AI Engineer',role_ids:['15-1252.00'],status:'confirmed'}],weekly_hours:6}});
    await api('/api/profiles/current/future','PUT',{role_id:'15-1252.00'});
    await page.goto(base+'/roadmap');
    await page.waitForFunction(()=>Array.from(document.querySelectorAll('button')).some(b=>b.textContent.includes('Research my target')&&!b.disabled));
    await page.locator('.job-pathway').screenshot({path:path.join(out,'desktop-start.png')});
    await page.setViewportSize({width:390,height:844});
    await page.locator('.job-pathway').screenshot({path:path.join(out,'mobile-start.png')});
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Mobile horizontal overflow');
    report.checks.push('Desktop/mobile initial view; no mobile horizontal overflow');
    await page.setViewportSize({width:1440,height:1000});
    if(providers){
      await page.getByRole('button',{name:'Research my target'}).click();
      await page.locator('.research-activity').waitFor({state:'visible'});
      await page.locator('.job-pathway').screenshot({path:path.join(out,'desktop-researching.png')});
      const runs=(await api('/api/pathway-research?role_id=15-1252.00')).runs;
      const run=await waitRun(runs[0].id);
      report.live_research={status:run.status,sources:run.sources.length,requirements:run.requirements.length,error:run.error,events:run.events};
      console.log(JSON.stringify(report.live_research));
      await page.reload();
      if(run.status==='review'){
        await page.getByText('Choose what belongs in your pathway.').waitFor();
        await page.locator('.job-pathway').screenshot({path:path.join(out,'desktop-review.png')});
        await page.setViewportSize({width:390,height:844});
        await page.locator('.research-review').screenshot({path:path.join(out,'mobile-review.png')});
        if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Mobile review overflow');
        report.checks.push('Real Tavily/OpenAI research reached pending review; no real requirements approved by automation');
      }
      else throw Error('Live research did not reach review: '+run.status);
    }
    if(proposalFixture){
      const draft=JSON.parse(fs.readFileSync(path.join(out,'planning-provider.json'),'utf8')).proposal;
      if(!draft)throw Error('Generate the isolated provider QA proposal first.');
      const date=new Date().toISOString();
      const fixture={id:'visual-fixture',role_id:'15-1252.00',target:'AI Engineer',market:'Malaysia',status:'ready',created_at:date,events:[],error:null,
        sources:[{id:'s1',title:'Synthetic QA requirement — not a job posting',url:null,origin:'manual',retrieved_at:date,location:'QA fixture',availability:'not_verified',reason:'Visual test fixture only.'}],
        requirements:[{id:'r1',source_id:'s1',title:'Reliable AI service — QA fixture',quote:'Design a reliable AI service and test failure modes.',priority:'required'}],
        review:{reviewed_at:date,reviewed_by:'automated_fixture',items:[{requirement_id:'r1',starting_point:'practice'}]},
        project:{...draft,title:'QA fixture · '+draft.title,accepted_at:null,accepted_by:null,milestones:draft.milestones.map((m,i)=>({...m,id:'fixture-'+i,note:'',status:'planned'}))}};
      await page.route(/\/api\/pathway-research\?/,route=>route.fulfill({json:{runs:[fixture]}}));
      await page.setViewportSize({width:1440,height:1000});
      await page.reload();
      await page.locator('.research-project').waitFor();
      await page.locator('.research-project').screenshot({path:path.join(out,'desktop-project-fixture.png')});
      await page.setViewportSize({width:390,height:844});
      await page.locator('.research-project').screenshot({path:path.join(out,'mobile-project-fixture.png')});
      if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Mobile project overflow');
      report.checks.push('Desktop/mobile project proposal with explicitly synthetic visual fixture; no persisted approval');
      fixture.project.accepted_at=date;
      fixture.evolution={id:'simulation-visual',mode:'simulation',status:'pending_review',message:'Review the task interpretation and proposed addition.',sources:[{id:'simulation-1',title:'Synthetic workflow fixture',url:null,statement:'Fictional assistant generates work requiring verification.',market:'Simulation',period:'Fictional',scope:'Hypothetical'}],draft:{reason:'Synthetic replay tests the review flow, not labour-market predictions.',implications:[{task:'Verify generated work',effect:'new_responsibility',explanation:'Generated output needs independent checks in this fictional scenario.',conditions:'Assume an assistant is available. This is not observed evidence.',source_ids:['simulation-1']}],addition:{...fixture.project.milestones[0],title:'Verify an assisted work sample'}}};
      await page.reload();
      await page.getByRole('button',{name:'Accept in simulation'}).waitFor();
      await page.locator('.pathway-evolution').screenshot({path:path.join(out,'mobile-evolution-fixture.png')});
      if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Mobile evolution overflow');
      await page.setViewportSize({width:1440,height:1000});
      await page.locator('.pathway-evolution').screenshot({path:path.join(out,'desktop-evolution-fixture.png')});
      report.checks.push('Synthetic update review: desktop/mobile, labelled simulation, no overflow');
    }
    report.browser_errors=errors;
    if(errors.length)throw Error('Browser runtime errors');
  }catch(error){
    report.failure=error.message;
    throw error;
  }finally{
    // Stop page requests before deleting its profile; always close the browser on cleanup failures.
    await page.close();
    try {
      if(pid){
        for(let attempt=0;attempt<3;attempt++){
          try {await api(`/api/profiles/${pid}`,'DELETE');report.fixture_deleted=true;break;}
          catch(error){if(attempt===2)throw error;await new Promise(r=>setTimeout(r,1500));}
        }
      }
    }finally{
      fs.writeFileSync(path.join(out,proposalFixture?'browser-fixture-report.json':'browser-report.json'),JSON.stringify(report,null,2));
      await browser.close();
    }
  }
  console.log(JSON.stringify(report));
})().catch(e=>{console.error(e.message);process.exitCode=1;});

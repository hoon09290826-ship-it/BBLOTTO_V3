(function(){
  'use strict';
  const VERSION='RC12.1-20260713-WINNING-BUTTON-FIX';
  const $=id=>document.getElementById(id);
  function token(){ try{return localStorage.getItem('bb_v34_token')||'';}catch(_){return '';} }
  async function request(path, options={}){
    const headers=Object.assign({'Content-Type':'application/json'}, options.headers||{});
    if(token()) headers.Authorization='Bearer '+token();
    const r=await fetch(path,Object.assign({},options,{headers,cache:'no-store'}));
    const text=await r.text(); let data={};
    try{ data=text?JSON.parse(text):{}; }catch(_){ data={raw:text}; }
    if(!r.ok){
      const e=data?.error?.message || data?.error || data?.detail || data?.message || text || '요청 실패';
      throw new Error(typeof e==='string'?e:JSON.stringify(e));
    }
    return data;
  }
  function markVersion(){
    let b=$('runtimeVersionBadge');
    if(!b){
      b=document.createElement('div'); b.id='runtimeVersionBadge';
      b.textContent='적용 버전 '+VERSION;
      b.style.cssText='position:fixed;right:10px;bottom:10px;z-index:2147483647;background:#111;color:#f6d878;border:1px solid #d4af37;border-radius:999px;padding:7px 11px;font:700 11px/1.2 Arial,sans-serif;pointer-events:none;opacity:.92';
      document.body.appendChild(b);
    }
    document.documentElement.dataset.bbRuntimeVersion=VERSION;
  }
  function closeLayers(){
    document.body.classList.remove('modal-open');
    document.querySelectorAll('.modal-backdrop,.quick-result-overlay').forEach(el=>{
      if(el.id==='memberQuickResultModal'){ el.remove(); return; }
      el.classList.remove('is-open'); el.setAttribute('aria-hidden','true');
      el.style.setProperty('display','none','important');
      el.style.setProperty('pointer-events','none','important');
      el.style.setProperty('visibility','hidden','important');
    });
  }
  function show(tab,label){
    closeLayers();
    document.querySelectorAll('.nav[data-tab]').forEach(x=>x.classList.toggle('active',x.dataset.tab===tab));
    document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
    const panel=$(tab); if(panel){ panel.classList.add('active'); panel.style.removeProperty('display'); }
    const title=$('pageTitle'); if(title) title.textContent=label||'';
    history.replaceState(null,'','#'+tab);
    window.scrollTo(0,0);
  }

  let searchedDraw=null;
  function renderSearch(d){
    const box=$('drawSearchResult'); if(!box) return;
    if(!d || !d.ok){ box.textContent=(d&&d.message)||'조회 결과가 없습니다.'; return; }
    const nums=(d.numbers||d.wins||[]).join(', ');
    box.innerHTML='<div class="draw-search-result"><b>'+Number(d.round_no||0)+'회</b> <small>'+(d.draw_date||'')+'</small><p>'+nums+(d.bonus!==undefined?' + '+d.bonus:'')+'</p><p>'+(d.message||'조회 완료')+'</p></div>';
  }
  async function searchDraw(btn){
    const round=Number($('drawSearchRound')?.value||0);
    if(!round){ alert('조회할 회차를 입력하세요.'); $('drawSearchRound')?.focus(); return; }
    if(btn){ btn.disabled=true; btn.dataset.oldText=btn.textContent; btn.textContent='조회 중...'; }
    try{
      const d=await request('/api/draws/search?round_no='+encodeURIComponent(round),{method:'GET'});
      searchedDraw=(d&&d.ok)?d:null; renderSearch(d);
    }catch(e){ searchedDraw=null; renderSearch({ok:false,message:'회차 조회 실패: '+(e.message||e)}); }
    finally{ if(btn){ btn.disabled=false; btn.textContent=btn.dataset.oldText||'회차 조회'; } }
  }
  function applyDraw(){
    if(!searchedDraw){ alert('먼저 회차 조회 버튼을 눌러 조회를 완료하세요.'); return; }
    const nums=searchedDraw.numbers||searchedDraw.wins||[];
    if($('checkRound')) $('checkRound').value=searchedDraw.round_no||'';
    if($('winningNums')) $('winningNums').value=nums.join(' ');
    if($('bonusNum')) $('bonusNum').value=searchedDraw.bonus??'';
    const info=$('autoRoundInfo'); if(info) info.textContent=(searchedDraw.round_no||'')+'회 당첨번호를 적용했습니다.';
  }

  async function runStats(limit,btn){
    if(btn){ btn.disabled=true; btn.dataset.oldText=btn.textContent; btn.textContent='불러오는 중...'; }
    try{
      if(typeof window.loadStats==='function') return await window.loadStats(limit);
      const d=await request('/api/stats?limit='+encodeURIComponent(limit));
      const box=$('statsBox');
      if(box){
        const hot=(d.hot||[]).join(', ')||'-', cold=(d.cold||[]).join(', ')||'-';
        box.innerHTML='<div class="stats-dashboard"><div class="stats-kpi"><div class="stat-card"><b>'+Number(d.count||0)+'</b><span>분석 회차</span></div><div class="stat-card"><b>'+String(d.latest_round||'-')+'</b><span>최신 회차</span></div></div><div class="detail-section"><h4>HOT 번호</h4><p>'+hot+'</p><h4>COLD 번호</h4><p>'+cold+'</p></div></div>';
      }
      return d;
    }catch(e){ alert('통계 불러오기 실패: '+(e.message||e)); }
    finally{ if(btn){ btn.disabled=false; btn.textContent=btn.dataset.oldText||btn.textContent; } }
  }
  async function runWinning(btn){
    if(btn){ btn.disabled=true; btn.dataset.oldText=btn.textContent; btn.textContent='확인 중...'; }
    try{
      const body={round_no:Number($('checkRound')?.value||0),winning:$('winningNums')?.value||'',bonus:Number($('bonusNum')?.value||0)};
      if(!body.round_no) throw new Error('회차를 입력해 주세요.');
      const d=await request('/api/check_winning',{method:'POST',body:JSON.stringify(body)});
      const box=$('winningResult'); if(box) box.textContent=(d.round_no||body.round_no)+'회차 당첨확인이 완료되었습니다.';
      return d;
    }catch(e){ alert('당첨확인 실패: '+(e.message||e)); }
    finally{ if(btn){ btn.disabled=false; btn.textContent=btn.dataset.oldText||btn.textContent; } }
  }
  function bind(){
    markVersion(); closeLayers();
    document.querySelectorAll('button:not([type])').forEach(b=>b.type='button');
    document.addEventListener('click',function(e){
      const nav=e.target.closest?.('.nav[data-tab]');
      if(nav){ e.preventDefault(); e.stopImmediatePropagation(); show(nav.dataset.tab||'dashboard',(nav.textContent||'').trim()); return; }
      const stat=e.target.closest?.('.statBtn');
      if(stat){ e.preventDefault(); e.stopImmediatePropagation(); runStats(Number(stat.dataset.limit||0),stat); return; }
      const search=e.target.closest?.('#searchDraw');
      if(search){ e.preventDefault(); e.stopImmediatePropagation(); searchDraw(search); return; }
      const apply=e.target.closest?.('#applySearchedDraw');
      if(apply){ e.preventDefault(); e.stopImmediatePropagation(); applyDraw(); return; }
      const win=e.target.closest?.('#checkWinning,#saveDraw');
      if(win){ e.preventDefault(); e.stopImmediatePropagation(); runWinning(win); return; }
    },true);
    $('drawSearchRound')?.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); searchDraw($('searchDraw')); } });
        window.addEventListener('hashchange',()=>{ const t=location.hash.slice(1); if($(t)) show(t,document.querySelector('.nav[data-tab="'+t+'"]')?.textContent?.trim()||''); });
    const initial=location.hash.slice(1); if(initial && $(initial)) show(initial,document.querySelector('.nav[data-tab="'+initial+'"]')?.textContent?.trim()||'');
  }
  window.BBLOTTO_CRITICAL={version:VERSION,showPanel:show,runStats,runWinning,searchDraw,applyDraw};
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',bind,{once:true}); else bind();
})();

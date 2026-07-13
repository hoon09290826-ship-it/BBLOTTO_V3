(function(){
  'use strict';
  const $=id=>document.getElementById(id);
  const run=(name,...args)=>{
    const fn=window[name];
    if(typeof fn!=='function'){
      console.error('[BUTTON RECOVERY] function missing:',name);
      const t=$('toast'); if(t){ t.textContent='기능을 불러오지 못했습니다. 새로고침 후 다시 시도해주세요.'; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2200); }
      return;
    }
    try{ const r=fn(...args); if(r&&typeof r.catch==='function') r.catch(e=>{ console.error(e); alert(e?.message||'처리 중 오류가 발생했습니다.'); }); }
    catch(e){ console.error(e); alert(e?.message||'처리 중 오류가 발생했습니다.'); }
  };
  function cleanupOldCaches(){
    try{ navigator.serviceWorker?.getRegistrations?.().then(rs=>rs.forEach(r=>r.unregister())).catch(()=>{}); }catch(_){ }
    try{ caches?.keys?.().then(keys=>Promise.all(keys.map(k=>caches.delete(k)))).catch(()=>{}); }catch(_){ }
  }
  cleanupOldCaches();
  document.addEventListener('click',function(e){
    const b=e.target?.closest?.('button'); if(!b) return;
    const nav=b.closest('button.nav[data-tab]');
    if(nav){
      e.preventDefault();
      const tab=String(nav.dataset.tab||'dashboard');
      document.querySelectorAll('.nav').forEach(x=>x.classList.toggle('active',x===nav));
      document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
      $(tab)?.classList.add('active');
      if($('pageTitle')) $('pageTitle').textContent=nav.textContent.trim();
      const loader={dashboard:'loadDashboard',members:'loadMembers',winning:'loadDraws',stats:'loadStats',account:'loadMyAccount',admin:'loadAdmin'}[tab];
      if(loader) run(loader, ...(tab==='stats'?[0]:[]));
      return;
    }
    if(b.classList.contains('statBtn')){ e.preventDefault(); e.stopImmediatePropagation(); run('loadStats',Number(b.dataset.limit||0)); return; }
    const map={
      checkWinning:'checkWinning', saveDraw:'saveDraw', searchDraw:'searchDrawByRound', applySearchedDraw:'applySearchedDrawToCheck',
      generate:'generate', addMember:'addMember', saveMemberBtn:'saveMember',
      rc44AutoUpdate:'rc44RunAutoUpdate', createBackup:'createBackup',
      saveMyProfile:'saveMyProfile', saveMyPassword:'saveMyPassword'
    };
    if(map[b.id]){ e.preventDefault(); e.stopImmediatePropagation(); run(map[b.id]); }
  },true);
})();

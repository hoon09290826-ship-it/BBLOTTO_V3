(function(){
  'use strict';
  function byId(id){ return document.getElementById(id); }
  function closeBlockingLayers(){
    document.body.classList.remove('modal-open');
    document.querySelectorAll('.modal-backdrop, .quick-result-overlay').forEach(function(el){
      if(el.id === 'memberQuickResultModal') el.remove();
      else {
        el.classList.remove('is-open');
        el.setAttribute('aria-hidden','true');
        el.style.setProperty('display','none','important');
        el.style.setProperty('pointer-events','none','important');
      }
    });
  }
  function showPanel(tab, title){
    closeBlockingLayers();
    document.querySelectorAll('button.nav[data-tab]').forEach(function(btn){
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tab);
    });
    document.querySelectorAll('.panel').forEach(function(panel){ panel.classList.remove('active'); });
    var target=byId(tab);
    if(target){
      target.classList.add('active');
      target.style.removeProperty('display');
    }
    var pageTitle=byId('pageTitle');
    if(pageTitle && title) pageTitle.textContent=title;
    try{ window.scrollTo(0,0); }catch(e){}
    // Main app data loaders are optional. Navigation must never depend on them.
    try{
      var loaders={
        dashboard:'loadDashboard', members:'loadMembers', stats:'loadStats',
        account:'loadMyAccount', admin:'loadAdmin'
      };
      if(tab==='winning'){
        if(typeof window.loadDraws==='function') Promise.resolve(window.loadDraws()).catch(console.error);
        if(typeof window.setNextDrawRound==='function') Promise.resolve(window.setNextDrawRound()).catch(console.error);
      } else {
        var name=loaders[tab];
        if(name && typeof window[name]==='function'){
          var arg=tab==='stats'?0:undefined;
          Promise.resolve(window[name](arg)).catch(console.error);
        }
      }
    }catch(e){ console.error('화면 데이터 로딩 실패',e); }
    return false;
  }
  function bindNavigation(){
    closeBlockingLayers();
    document.querySelectorAll('button:not([type])').forEach(function(btn){ btn.type='button'; });
    document.querySelectorAll('button.nav[data-tab]').forEach(function(btn){
      btn.onclick=function(ev){
        if(ev){ ev.preventDefault(); ev.stopPropagation(); }
        return showPanel(btn.getAttribute('data-tab')||'dashboard', (btn.textContent||'').trim());
      };
    });
    // Capture fallback: even if another script stops bubbling, menu clicks still switch panels.
    document.addEventListener('pointerup',function(ev){
      var btn=ev.target && ev.target.closest ? ev.target.closest('button.nav[data-tab]') : null;
      if(!btn) return;
      ev.preventDefault();
      showPanel(btn.getAttribute('data-tab')||'dashboard', (btn.textContent||'').trim());
    },true);
  }
  // Remove every old service worker/cache so deployed browsers cannot keep stale JS/CSS.
  try{
    if('serviceWorker' in navigator){
      navigator.serviceWorker.getRegistrations().then(function(rs){ rs.forEach(function(r){ r.unregister(); }); });
    }
    if(window.caches){ caches.keys().then(function(keys){ keys.forEach(function(k){ caches.delete(k); }); }); }
  }catch(e){ console.warn(e); }
  window.bbShowPanel=showPanel;
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',bindNavigation,{once:true});
  else bindNavigation();
  window.addEventListener('load',bindNavigation,{once:true});
})();

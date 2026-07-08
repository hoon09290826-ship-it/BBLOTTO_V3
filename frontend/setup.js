const $ = id => document.getElementById(id);
async function checkSetup(){
  try{
    const r = await fetch('/api/setup/status');
    const d = await r.json();
    if(!d.needs_setup) location.href='/';
  }catch(e){}
}
async function createAdmin(){
  const username=$('setupId').value.trim();
  const name=$('setupName').value.trim() || '대표 관리자';
  const password=$('setupPw').value;
  const confirm=$('setupPw2').value;
  if(!username || !password){ $('setupMsg').textContent='아이디와 비밀번호를 입력하세요.'; return; }
  if(password.length < 8){ $('setupMsg').textContent='비밀번호는 8자리 이상으로 입력하세요.'; return; }
  if(password !== confirm){ $('setupMsg').textContent='비밀번호 확인이 일치하지 않습니다.'; return; }
  $('setupMsg').textContent='관리자 생성 중...';
  try{
    const r=await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,name,password,confirm})});
    if(!r.ok) throw new Error(await r.text());
    $('setupMsg').textContent='생성 완료. 로그인 화면으로 이동합니다.';
    setTimeout(()=>location.href='/',800);
  }catch(e){ $('setupMsg').textContent='생성 실패: '+e.message; }
}
checkSetup();
$('setupBtn').addEventListener('click', createAdmin);
$('setupPw2').addEventListener('keydown',e=>{ if(e.key==='Enter') createAdmin(); });

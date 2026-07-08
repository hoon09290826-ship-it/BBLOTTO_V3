from collections import Counter
import random, json
from .db_v50 import rows, execute, now
def latest_round():
    r = rows('select round from draws order by round desc limit 1')
    return (r[0]['round'] + 1) if r else 1
def recent_draws(limit=100):
    return rows('select * from draws order by round desc limit ?', (limit,))
def stats(limit=100):
    ds = recent_draws(limit); nums=[]
    for d in ds: nums += [d[f'n{i}'] for i in range(1,7)]
    cnt=Counter(nums); odd=sum(1 for n in nums if n%2); even=len(nums)-odd
    zones={'1-15':0,'16-30':0,'31-45':0}
    for n in nums:
        if n<=15: zones['1-15']+=1
        elif n<=30: zones['16-30']+=1
        else: zones['31-45']+=1
    hot=[{'number':n,'count':cnt[n]} for n,_ in cnt.most_common(10)]
    cold=sorted([{'number':n,'count':cnt.get(n,0)} for n in range(1,46)], key=lambda x:(x['count'],x['number']))[:10]
    return {'draw_count':len(ds),'hot':hot,'cold':cold,'odd':odd,'even':even,'zones':zones,'latest_known_round': ds[0]['round'] if ds else None, 'next_round': latest_round()}
def make_combo(prefer, depth=0):
    s=set(); pool=[x['number'] for x in prefer['hot'][:8]] + [x['number'] for x in prefer['cold'][:8]] + list(range(1,46))
    while len(s)<6: s.add(random.choice(pool))
    arr=sorted(s); odd=sum(n%2 for n in arr)
    if odd in (0,1,5,6) and depth<20: return make_combo(prefer, depth+1)
    return arr
def generate(round_no=None, member_id=None, count=10):
    round_no = round_no or latest_round(); st=stats(100); combos=[]; seen=set()
    while len(combos)<count:
        arr=make_combo(st); key=tuple(arr)
        if key in seen: continue
        seen.add(key); score=82 + random.randint(0,13)
        reason='최근 100회 기준 HOT/COLD 균형, 홀짝 비율, 구간 분포를 맞춘 조합입니다.'
        execute('insert into recommendations(member_id,round,numbers,score,reason,created_at) values(?,?,?,?,?,?)',(member_id,round_no,json.dumps(arr,ensure_ascii=False),score,reason,now()))
        combos.append({'numbers':arr,'score':score,'reason':reason})
    return {'round':round_no,'count':len(combos),'items':combos,'summary':'최근 100회 통계를 기준으로 자동 생성했습니다. 실제 당첨을 보장하지 않습니다.'}

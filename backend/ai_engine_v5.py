"""BBLOTTO AI V5 cached full-history recommendation engine.

목표
- DB에 저장된 1회차~현재 회차 전체 당첨번호를 한 번 분석해 캐시 저장
- 추천번호 생성 버튼은 캐시를 읽어 빠르게 후보 생성/점수화
- 새 회차가 추가되면 자동으로 캐시 재생성
"""
from __future__ import annotations

import itertools
import json
import random
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "database" / "bblotto_v34.db"
ALT_DB_PATH = BASE / "database" / "lotto.db"
CACHE_PATH = BASE / "database" / "ai_v5_analysis_cache.json"
ENGINE_VERSION = "BBLOTTO_AI_V5_FULL_HISTORY_CACHE_FAST"


def _conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def _parse_nums(value: Any) -> List[int]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw = value
    else:
        text = str(value).strip()
        if not text:
            return []
        try:
            obj = json.loads(text)
            raw = obj if isinstance(obj, list) else []
        except Exception:
            raw = text.replace("/", ",").replace("|", ",").replace("-", ",").split(",")
    nums: List[int] = []
    for x in raw:
        try:
            n = int(str(x).strip())
            if 1 <= n <= 45 and n not in nums:
                nums.append(n)
        except Exception:
            pass
    return sorted(nums)


def _load_draws_from_db(db_path: Path) -> List[Dict[str, Any]]:
    """draws 테이블이 n1~n6 구조이든 numbers JSON 구조이든 모두 읽는다."""
    if not db_path.exists():
        return []
    with _conn(db_path) as con:
        try:
            cols = {r[1] for r in con.execute("PRAGMA table_info(draws)").fetchall()}
            rows = con.execute("SELECT * FROM draws ORDER BY round_no DESC").fetchall()
        except Exception:
            return []
    draws: List[Dict[str, Any]] = []
    for r in rows:
        try:
            if "numbers" in cols:
                nums = _parse_nums(r["numbers"])
            else:
                nums = _parse_nums([r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"]])
            if len(nums) == 6:
                draws.append({
                    "r": int(r["round_no"]),
                    "d": str(r["draw_date"] or ""),
                    "n": nums,
                    "b": int(r["bonus"] or 0),
                })
        except Exception:
            continue
    return draws


def _load_draws() -> List[Dict[str, Any]]:
    """메인 DB와 보조 DB를 합쳐 최신 회차 기준으로 중복 없이 읽는다."""
    merged: Dict[int, Dict[str, Any]] = {}
    for db_path in (DB_PATH, ALT_DB_PATH):
        for d in _load_draws_from_db(db_path):
            r = int(d.get("r") or 0)
            if r <= 0:
                continue
            # 같은 회차가 있으면 메인 DB 값을 우선 유지한다.
            if r not in merged or db_path == DB_PATH:
                merged[r] = d
    return sorted(merged.values(), key=lambda x: int(x["r"]), reverse=True)


def _flatten(draws: Sequence[Dict[str, Any]]) -> List[int]:
    out: List[int] = []
    for d in draws:
        out.extend(_parse_nums(d.get("n")))
    return out


def _coverage(draws: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    rounds = sorted({int(d["r"]) for d in draws if int(d.get("r") or 0) > 0})
    if not rounds:
        return {"is_full_history": False, "missing_count": 0, "missing_sample": [], "round_range": []}
    mn, mx = rounds[0], rounds[-1]
    expected = set(range(1, mx + 1))
    missing = sorted(expected - set(rounds))
    return {
        "is_full_history": mn == 1 and len(missing) == 0,
        "missing_count": len(missing),
        "missing_sample": missing[:30],
        "round_range": [mn, mx],
        "expected_count": mx,
        "actual_count": len(rounds),
    }


def _ac(nums: Sequence[int]) -> int:
    arr = sorted(nums)
    diffs = {abs(b-a) for i, a in enumerate(arr) for b in arr[i+1:]}
    return max(0, len(diffs) - 5)


def _zones(nums: Sequence[int]) -> List[int]:
    return [sum(1 <= n <= 15 for n in nums), sum(16 <= n <= 30 for n in nums), sum(31 <= n <= 45 for n in nums)]


def _consecutive(nums: Sequence[int]) -> int:
    arr = sorted(nums)
    return sum(1 for i in range(1, len(arr)) if arr[i] == arr[i-1] + 1)


def _end_dup(nums: Sequence[int]) -> int:
    c = Counter(n % 10 for n in nums)
    return max(c.values()) if c else 0


def _weighted_frequency(draws: Sequence[Dict[str, Any]]) -> Dict[int, float]:
    """최근 회차일수록 조금 더 높은 가중치. 전체 장기 데이터도 함께 반영."""
    scores = {n: 0.0 for n in range(1, 46)}
    total = max(1, len(draws))
    # draws는 최신순. 최신 1.65배, 오래된 회차 0.75배 근처.
    for idx, d in enumerate(draws):
        recency = 1.65 - (idx / max(1, total - 1)) * 0.90
        for n in d["n"]:
            scores[n] += recency
    return scores


def _number_gaps(draws: Sequence[Dict[str, Any]]) -> Dict[int, int]:
    gaps = {n: len(draws) + 1 for n in range(1, 46)}
    for idx, d in enumerate(draws):
        for n in d["n"]:
            if gaps[n] == len(draws) + 1:
                gaps[n] = idx
    return gaps


def _build_cache() -> Dict[str, Any]:
    draws = _load_draws()
    if not draws:
        return {"engine_version": ENGINE_VERSION, "draw_count": 0, "latest_round": 0, "error": "당첨번호 DB가 비어 있습니다."}

    latest_round = max(d["r"] for d in draws)
    draw_count = len(draws)
    coverage = _coverage(draws)
    all_nums = _flatten(draws)
    recent10 = draws[:10]
    recent30 = draws[:30]
    recent50 = draws[:50]
    recent100 = draws[:100]
    recent300 = draws[:300]

    freq_all = Counter(all_nums)
    freq10 = Counter(_flatten(recent10))
    freq30 = Counter(_flatten(recent30))
    freq50 = Counter(_flatten(recent50))
    freq100 = Counter(_flatten(recent100))
    freq300 = Counter(_flatten(recent300))
    weighted = _weighted_frequency(draws)
    gaps = _number_gaps(draws)

    pair_all: Counter = Counter()
    triple300: Counter = Counter()
    for d in draws:
        pair_all.update(tuple(sorted(p)) for p in itertools.combinations(d["n"], 2))
    for d in recent300:
        triple300.update(tuple(sorted(t)) for t in itertools.combinations(d["n"], 3))

    def rank(counter: Counter, reverse: bool = True) -> List[int]:
        return sorted(range(1, 46), key=lambda n: ((-counter.get(n, 0), n) if reverse else (counter.get(n, 0), n)))

    score_map: Dict[int, float] = {}
    for n in range(1, 46):
        score_map[n] = round(
            freq_all.get(n, 0) * 0.18
            + freq300.get(n, 0) * 0.45
            + freq100.get(n, 0) * 0.75
            + freq50.get(n, 0) * 0.95
            + freq30.get(n, 0) * 1.15
            + freq10.get(n, 0) * 1.45
            + weighted.get(n, 0) * 0.22
            + min(10, gaps.get(n, 0)) * 0.12,
            4,
        )

    hot = sorted(range(1, 46), key=lambda n: (-score_map[n], n))
    cold = sorted(range(1, 46), key=lambda n: (score_map[n], n))
    overdue = sorted(range(1, 46), key=lambda n: (-gaps.get(n, 0), n))
    mid = sorted(range(1, 46), key=lambda n: (abs(score_map[n] - sum(score_map.values()) / 45), n))

    sums30 = [sum(d["n"]) for d in recent30] or [135]
    acs30 = [_ac(d["n"]) for d in recent30] or [7]

    cache = {
        "engine_version": ENGINE_VERSION,
        "created_at": int(time.time()),
        "draw_count": draw_count,
        "latest_round": latest_round,
        "next_round": latest_round + 1,
        "round_range": coverage.get("round_range") or [min(d["r"] for d in draws), latest_round],
        "is_full_history": bool(coverage.get("is_full_history")),
        "missing_rounds_count": int(coverage.get("missing_count") or 0),
        "missing_rounds_sample": coverage.get("missing_sample") or [],
        "expected_count": coverage.get("expected_count"),
        "actual_count": coverage.get("actual_count"),
        "hot": hot,
        "cold": cold,
        "overdue": overdue,
        "mid": mid,
        "score_map": {str(k): v for k, v in score_map.items()},
        "gap": {str(k): int(v) for k, v in gaps.items()},
        "frequency_all": {str(n): int(freq_all.get(n, 0)) for n in range(1, 46)},
        "frequency10": {str(n): int(freq10.get(n, 0)) for n in range(1, 46)},
        "frequency30": {str(n): int(freq30.get(n, 0)) for n in range(1, 46)},
        "frequency100": {str(n): int(freq100.get(n, 0)) for n in range(1, 46)},
        "frequency300": {str(n): int(freq300.get(n, 0)) for n in range(1, 46)},
        "pair_top": [[list(k), int(v)] for k, v in pair_all.most_common(80)],
        "triple_top": [[list(k), int(v)] for k, v in triple300.most_common(50)],
        "avg_sum30": round(sum(sums30) / len(sums30), 1),
        "avg_ac30": round(sum(acs30) / len(acs30), 1),
        "end_counts": {str(k): int(v) for k, v in Counter(n % 10 for n in _flatten(recent30)).items()},
        "zone_counts": _zones(_flatten(recent30)),
        "latest": draws[0],
    }
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    return cache


def _cache_valid(cache: Dict[str, Any], draws: Sequence[Dict[str, Any]]) -> bool:
    if not cache or not draws:
        return False
    return int(cache.get("draw_count") or 0) == len(draws) and int(cache.get("latest_round") or 0) == max(d["r"] for d in draws)


def get_analysis_cache(force: bool = False) -> Dict[str, Any]:
    draws = _load_draws()
    if force or not CACHE_PATH.exists():
        return _build_cache()
    try:
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _build_cache()
    if not _cache_valid(cache, draws):
        return _build_cache()
    return cache


def latest_stats(limit: int = 0) -> Dict[str, Any]:
    c = get_analysis_cache(False)
    return {
        "engine_version": c.get("engine_version", ENGINE_VERSION),
        "latest_round": c.get("latest_round", 0),
        "next_round": c.get("next_round", 0),
        "draw_count": c.get("draw_count", 0),
        "round_range": c.get("round_range", []),
        "is_full_history": c.get("is_full_history", False),
        "missing_rounds_count": c.get("missing_rounds_count", 0),
        "missing_rounds_sample": c.get("missing_rounds_sample", []),
        "hot": c.get("hot", [])[:12],
        "cold": c.get("cold", [])[:12],
        "overdue": c.get("overdue", [])[:12],
        "pair_top": c.get("pair_top", [])[:10],
        "avg_sum30": c.get("avg_sum30", 0),
        "avg_ac30": c.get("avg_ac30", 0),
        "end_counts": c.get("end_counts", {}),
        "zone_counts": c.get("zone_counts", []),
    }


def _weights(cache: Dict[str, Any], mode: str, grade: str) -> Dict[int, float]:
    smap = {int(k): float(v) for k, v in (cache.get("score_map") or {}).items()}
    hot = set(cache.get("hot", [])[:14])
    cold = set(cache.get("cold", [])[:14])
    overdue = set(cache.get("overdue", [])[:16])
    mid = set(cache.get("mid", [])[:18])
    weights: Dict[int, float] = {}
    avg = sum(smap.values()) / max(1, len(smap))
    for n in range(1, 46):
        w = 1.0 + (smap.get(n, avg) / max(1.0, avg))
        if n in hot:
            w += 1.25
        if n in overdue:
            w += 0.85
        if n in cold:
            w += 0.45
        if n in mid:
            w += 0.35
        if mode == "conservative" and 11 <= n <= 35:
            w += 0.55
        elif mode == "aggressive" and (n <= 12 or n >= 34):
            w += 0.45
        if grade == "1등":
            w *= 1.08 if n in hot or n in overdue else 1.0
        elif grade == "2등":
            w *= 1.04
        weights[n] = max(0.2, w)
    return weights


def _pick(weights: Dict[int, float], banned: set[int]) -> int:
    items = [(n, w) for n, w in weights.items() if n not in banned]
    total = sum(w for _, w in items)
    r = random.random() * total
    for n, w in items:
        r -= w
        if r <= 0:
            return n
    return items[-1][0]


def _signature(nums: Sequence[int]) -> Dict[str, Any]:
    nums = sorted(nums)
    odd = sum(n % 2 for n in nums)
    return {
        "sum": sum(nums),
        "odd": odd,
        "even": 6 - odd,
        "zones": _zones(nums),
        "ac": _ac(nums),
        "cons": _consecutive(nums),
        "end_dup": _end_dup(nums),
    }


def _combo_score(nums: Sequence[int], cache: Dict[str, Any], mode: str, grade: str) -> Tuple[float, List[str], Dict[str, Any]]:
    nums = sorted(nums)
    sig = _signature(nums)
    smap = {int(k): float(v) for k, v in (cache.get("score_map") or {}).items()}
    gaps = {int(k): int(v) for k, v in (cache.get("gap") or {}).items()}
    pair = {tuple(x[0]): int(x[1]) for x in cache.get("pair_top", [])}
    hot = set(cache.get("hot", [])[:14])
    cold = set(cache.get("cold", [])[:14])
    overdue = set(cache.get("overdue", [])[:16])

    s = 55.0
    s += {3: 9.0, 2: 7.0, 4: 7.0, 1: 1.5, 5: 1.5}.get(sig["odd"], -5)
    s += 9.0 if 105 <= sig["sum"] <= 180 else 4.0 if 90 <= sig["sum"] <= 195 else -8.0
    s += 8.0 if max(sig["zones"]) <= 3 and min(sig["zones"]) >= 1 else -8.0
    s += 6.0 if 6 <= sig["ac"] <= 10 else 2.0 if 5 <= sig["ac"] <= 11 else -5.0
    s += 3.5 if sig["cons"] <= 1 else -4.0
    s += 3.5 if sig["end_dup"] <= 2 else -4.0
    s += min(8.0, sum(smap.get(n, 0) for n in nums) / max(1, len(nums)) * 0.15)
    s += min(5.0, len(set(nums) & hot) * 1.3)
    s += min(4.0, len(set(nums) & overdue) * 1.1)
    s += min(2.5, len(set(nums) & cold) * 0.65)
    if len(set(nums) & hot) >= 5 or len(set(nums) & overdue) >= 5:
        s -= 3.5
    pair_hits = 0
    pair_score = 0
    for p in itertools.combinations(nums, 2):
        v = pair.get(tuple(sorted(p)), 0)
        if v:
            pair_hits += 1
            pair_score += v
    s += min(4.5, pair_score / 18.0) + min(2.0, pair_hits * 0.35)
    gap_avg = sum(gaps.get(n, 0) for n in nums) / 6.0
    s += 2.5 if 2 <= gap_avg <= 14 else 1.0 if gap_avg < 25 else -1.5
    if grade == "1등":
        s += 4.8
    elif grade == "2등":
        s += 3.2
    s += ((sum(n*n for n in nums) + sum(nums) * 7) % 31 - 15) * 0.055
    s = round(max(72.0, min(99.1, s)), 1)

    reasons = []
    if len(set(nums) & hot): reasons.append(f"최근/누적 상승수 {len(set(nums)&hot)}개 반영")
    if len(set(nums) & overdue): reasons.append(f"미출현 GAP 보정수 {len(set(nums)&overdue)}개 포함")
    if pair_hits: reasons.append(f"동반출현 페어 {pair_hits}개 반영")
    reasons.append(f"홀짝 {sig['odd']}:{sig['even']} · 합계 {sig['sum']} · AC {sig['ac']}")
    return s, reasons[:4], sig


def _valid(nums: Sequence[int]) -> bool:
    sig = _signature(nums)
    if len(set(nums)) != 6:
        return False
    if sig["odd"] not in (2, 3, 4):
        return False
    if max(sig["zones"]) > 4 or min(sig["zones"]) == 0:
        return False
    if sig["sum"] < 85 or sig["sum"] > 200:
        return False
    if sig["cons"] > 2:
        return False
    if sig["end_dup"] > 3:
        return False
    return True


def make_premium_combos(count: int = 10, fixed: Any = "", excluded: Any = "", mode: str = "balanced", member_grade: str = "일반", member_id: Optional[int] = None):
    started = time.perf_counter()
    count = max(1, min(int(count or 10), 50))
    cache = get_analysis_cache(False)
    grade = "1등" if str(member_grade) == "1등" else "2등" if str(member_grade) == "2등" else "일반"
    fixed_nums = _parse_nums(fixed)[:6]
    excluded_nums = set(_parse_nums(excluded)) - set(fixed_nums)
    weights = _weights(cache, mode or "balanced", grade)
    for n in excluded_nums:
        weights.pop(n, None)

    # 캐시 기반이라 후보 6천~1만2천개도 빠르게 처리 가능. 등급별로 후보량만 차등.
    target_candidates = {"일반": 6500, "2등": 9000, "1등": 12000}.get(grade, 6500)
    target_candidates = max(target_candidates, count * 700)
    candidates: List[Tuple[float, List[int], List[str], Dict[str, Any]]] = []
    seen: set[Tuple[int, ...]] = set()
    attempts = 0
    while attempts < target_candidates and len(candidates) < target_candidates // 2:
        attempts += 1
        selected = set(fixed_nums)
        guard = 0
        while len(selected) < 6 and guard < 60:
            guard += 1
            selected.add(_pick(weights, selected | excluded_nums))
        nums = sorted(selected)
        key = tuple(nums)
        if key in seen or len(nums) != 6 or not _valid(nums):
            continue
        seen.add(key)
        score, reasons, sig = _combo_score(nums, cache, mode or "balanced", grade)
        candidates.append((score, nums, reasons, sig))

    candidates.sort(key=lambda x: (-x[0], x[1]))
    selected: List[List[int]] = []
    details: List[Dict[str, Any]] = []
    usage = Counter()
    pair_usage = Counter()
    for score, nums, reasons, sig in candidates:
        s = set(nums)
        if any(len(s & set(prev)) >= 5 for prev in selected):
            continue
        if any(usage[n] >= max(3, count // 3 + 1) for n in nums):
            continue
        pairs = [tuple(sorted(p)) for p in itertools.combinations(nums, 2)]
        if any(pair_usage[p] >= 2 for p in pairs):
            continue
        selected.append(nums)
        usage.update(nums)
        pair_usage.update(pairs)
        details.append({
            "numbers": nums,
            "score": score,
            "ai_score": score,
            "vip_score": score,
            "grade": "VIP" if score >= 95 else "PREMIUM" if score >= 91 else "NORMAL",
            "member_grade": grade,
            "reason": " / ".join(reasons),
            "reasons": reasons,
            "sum": sig["sum"],
            "odd": sig["odd"],
            "even": sig["even"],
            "ac": sig["ac"],
            "zones": sig["zones"],
            "engine": ENGINE_VERSION,
        })
        if len(selected) >= count:
            break

    # 혹시 필터가 너무 강하면 상위 후보로 보충
    for score, nums, reasons, sig in candidates:
        if len(selected) >= count:
            break
        if nums not in selected:
            selected.append(nums)
            details.append({"numbers": nums, "score": score, "ai_score": score, "vip_score": score, "grade": "NORMAL", "member_grade": grade, "reason": " / ".join(reasons), "reasons": reasons, "sum": sig["sum"], "odd": sig["odd"], "even": sig["even"], "ac": sig["ac"], "zones": sig["zones"], "engine": ENGINE_VERSION})

    st = latest_stats()
    st.update({
        "engine_version": ENGINE_VERSION,
        "member_grade": grade,
        "ai_v5_candidates": len(candidates),
        "ai_v5_attempts": attempts,
        "ai_v4_candidates": len(candidates),  # 기존 화면 호환
        "ai_v4_attempts": attempts,
        "cache_file": str(CACHE_PATH.name),
        "cache_used": True,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        "full_history": bool(st.get("is_full_history")),
        "is_full_history": bool(st.get("is_full_history")),
        "missing_rounds_count": st.get("missing_rounds_count", 0),
        "analysis_range": st.get("round_range"),
        "hot": st.get("hot", []),
        "cold": st.get("cold", []),
        "overdue": st.get("overdue", []),
    })
    return selected[:count], details[:count], st

# ---- 선택 실행용: 공식 동행복권 API로 1회차~최신회차 DB 보강 ----
def _official_fetch(round_no: int, timeout: int = 6) -> Optional[Dict[str, Any]]:
    import urllib.request
    url = f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={int(round_no)}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as res:
            data = json.loads(res.read().decode("utf-8"))
        if data.get("returnValue") != "success":
            return None
        nums = [int(data[f"drwtNo{i}"]) for i in range(1, 7)]
        return {"r": int(data["drwNo"]), "d": str(data.get("drwNoDate") or ""), "n": nums, "b": int(data["bnusNo"])}
    except Exception:
        return None


def _save_draw(draw: Dict[str, Any]) -> None:
    with _conn() as con:
        cols = {r[1] for r in con.execute("PRAGMA table_info(draws)").fetchall()}
        if "numbers" in cols:
            con.execute(
                """INSERT OR REPLACE INTO draws(round_no, draw_date, numbers, bonus, source, updated_at)
                   VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)""",
                (int(draw["r"]), draw.get("d", ""), json.dumps(draw["n"], ensure_ascii=False), int(draw.get("b") or 0), "official_full_sync"),
            )
        else:
            con.execute(
                """INSERT OR REPLACE INTO draws(round_no, draw_date, n1,n2,n3,n4,n5,n6, bonus, source)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (int(draw["r"]), draw.get("d", ""), *draw["n"], int(draw.get("b") or 0), "official_full_sync"),
            )


def sync_official_full_history(max_round: Optional[int] = None, stop_after_miss: int = 3) -> Dict[str, Any]:
    """1회차부터 최신회차까지 누락된 회차를 공식 API로 보강한다.

    배포 서버에서 한 번만 실행하면 이후 추천 생성은 캐시만 사용한다.
    max_round가 없으면 현재 DB의 최대 회차까지 누락분을 채우고, 그 다음 회차부터는 실패가 연속 발생할 때까지 최신 회차를 찾는다.
    """
    before = _load_draws()
    existing = {int(d["r"]) for d in before}
    latest_known = max(existing) if existing else 1
    target = int(max_round or latest_known)
    saved = 0
    failed = 0

    for r in range(1, target + 1):
        if r in existing:
            continue
        d = _official_fetch(r)
        if d:
            _save_draw(d); saved += 1; existing.add(r)
        else:
            failed += 1

    # 최신 회차 자동 탐색: DB 최대회차 이후 성공하는 동안 계속 저장
    if max_round is None:
        miss = 0
        r = max(existing) + 1 if existing else 1
        while miss < max(1, int(stop_after_miss)):
            d = _official_fetch(r)
            if d:
                _save_draw(d); saved += 1; existing.add(r); miss = 0
            else:
                miss += 1
            r += 1

    cache = get_analysis_cache(True)
    return {
        "ok": True,
        "saved": saved,
        "failed": failed,
        "draw_count_before": len(before),
        "draw_count_after": cache.get("draw_count"),
        "round_range": cache.get("round_range"),
        "latest_round": cache.get("latest_round"),
        "cache_rebuilt": True,
        "engine_version": ENGINE_VERSION,
    }

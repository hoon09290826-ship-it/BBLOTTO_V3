"""BBLOTTO AI V6 persistent full-history cache engine.

핵심 목표
- 당첨번호 DB의 1회차~최신회차 전체를 분석한다.
- 분석 결과를 JSON 파일이 아니라 DB 테이블(ai_analysis_cache)에 저장한다.
- 추천번호 생성 버튼은 저장된 캐시만 읽어 빠르게 동작한다.
- DB에 1회차~1231회차가 모두 있는지 상태값으로 확인할 수 있다.
"""
from __future__ import annotations

import itertools
import json
import random
import sqlite3
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "database" / "bblotto_v34.db"
ALT_DB_PATH = BASE / "database" / "lotto.db"
ENGINE_VERSION = "BBLOTTO_AI_V6_DB_FULL_HISTORY_CACHE"
CACHE_KEY = "v6_full_history_weighted"
MIN_REQUIRED_ROUND = 1
DEFAULT_TARGET_ROUND = 1231


def _conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def _parse_nums(value: Any) -> List[int]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw = list(value)
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
                draws.append({"r": int(r["round_no"]), "d": str(r["draw_date"] or ""), "n": nums, "b": int(r["bonus"] or 0)})
        except Exception:
            continue
    return draws


def _load_draws() -> List[Dict[str, Any]]:
    merged: Dict[int, Dict[str, Any]] = {}
    # 보조 DB를 먼저 넣고, 메인 DB가 있으면 덮어쓴다.
    for db_path in (ALT_DB_PATH, DB_PATH):
        for d in _load_draws_from_db(db_path):
            if int(d["r"]) > 0:
                merged[int(d["r"])] = d
    return sorted(merged.values(), key=lambda x: int(x["r"]), reverse=True)


def _flatten(draws: Sequence[Dict[str, Any]]) -> List[int]:
    out: List[int] = []
    for d in draws:
        out.extend(_parse_nums(d.get("n")))
    return out


def _coverage(draws: Sequence[Dict[str, Any]], target_round: Optional[int] = None) -> Dict[str, Any]:
    rounds = sorted({int(d["r"]) for d in draws if int(d.get("r") or 0) > 0})
    if not rounds:
        return {"is_full_history": False, "missing_count": 0, "missing_sample": [], "round_range": [], "expected_count": 0, "actual_count": 0}
    mn, mx = rounds[0], rounds[-1]
    target = int(target_round or mx)
    expected = set(range(MIN_REQUIRED_ROUND, target + 1))
    missing = sorted(expected - set(rounds))
    return {
        "is_full_history": mn == MIN_REQUIRED_ROUND and len(missing) == 0 and mx >= target,
        "missing_count": len(missing),
        "missing_sample": missing[:50],
        "round_range": [mn, mx],
        "expected_count": target,
        "actual_count": len([r for r in rounds if MIN_REQUIRED_ROUND <= r <= target]),
        "target_round": target,
    }


def _ac(nums: Sequence[int]) -> int:
    arr = sorted(nums)
    diffs = {abs(b - a) for i, a in enumerate(arr) for b in arr[i + 1:]}
    return max(0, len(diffs) - 5)


def _zones(nums: Sequence[int]) -> List[int]:
    return [sum(1 <= n <= 15 for n in nums), sum(16 <= n <= 30 for n in nums), sum(31 <= n <= 45 for n in nums)]


def _consecutive(nums: Sequence[int]) -> int:
    arr = sorted(nums)
    return sum(1 for i in range(1, len(arr)) if arr[i] == arr[i - 1] + 1)


def _end_dup(nums: Sequence[int]) -> int:
    c = Counter(n % 10 for n in nums)
    return max(c.values()) if c else 0


def _weighted_frequency(draws: Sequence[Dict[str, Any]]) -> Dict[int, float]:
    scores = {n: 0.0 for n in range(1, 46)}
    total = max(1, len(draws))
    for idx, d in enumerate(draws):  # 최신순
        recency = 1.70 - (idx / max(1, total - 1)) * 0.95
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


def _ensure_cache_table() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_analysis_cache (
                cache_key TEXT PRIMARY KEY,
                engine_version TEXT NOT NULL,
                latest_round INTEGER NOT NULL DEFAULT 0,
                draw_count INTEGER NOT NULL DEFAULT 0,
                target_round INTEGER NOT NULL DEFAULT 0,
                is_full_history INTEGER NOT NULL DEFAULT 0,
                missing_rounds_count INTEGER NOT NULL DEFAULT 0,
                payload TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )


def _read_cache_from_db() -> Optional[Dict[str, Any]]:
    _ensure_cache_table()
    with _conn(DB_PATH) as con:
        row = con.execute("SELECT payload FROM ai_analysis_cache WHERE cache_key=?", (CACHE_KEY,)).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["payload"])
    except Exception:
        return None


def _write_cache_to_db(cache: Dict[str, Any]) -> None:
    _ensure_cache_table()
    payload = json.dumps(cache, ensure_ascii=False, separators=(",", ":"))
    now = int(time.time())
    with _conn(DB_PATH) as con:
        con.execute(
            """
            INSERT INTO ai_analysis_cache(cache_key, engine_version, latest_round, draw_count, target_round,
                                          is_full_history, missing_rounds_count, payload, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(cache_key) DO UPDATE SET
                engine_version=excluded.engine_version,
                latest_round=excluded.latest_round,
                draw_count=excluded.draw_count,
                target_round=excluded.target_round,
                is_full_history=excluded.is_full_history,
                missing_rounds_count=excluded.missing_rounds_count,
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            (
                CACHE_KEY,
                ENGINE_VERSION,
                int(cache.get("latest_round") or 0),
                int(cache.get("draw_count") or 0),
                int(cache.get("target_round") or 0),
                1 if cache.get("is_full_history") else 0,
                int(cache.get("missing_rounds_count") or 0),
                payload,
                now,
                now,
            ),
        )


def _build_cache(target_round: Optional[int] = None) -> Dict[str, Any]:
    draws = _load_draws()
    if not draws:
        cache = {"engine_version": ENGINE_VERSION, "draw_count": 0, "latest_round": 0, "target_round": int(target_round or DEFAULT_TARGET_ROUND), "error": "당첨번호 DB가 비어 있습니다."}
        _write_cache_to_db(cache)
        return cache

    latest_round = max(d["r"] for d in draws)
    target = int(target_round or max(DEFAULT_TARGET_ROUND, latest_round))
    coverage = _coverage(draws, target)
    all_nums = _flatten(draws)
    recent10, recent30, recent50, recent100, recent300 = draws[:10], draws[:30], draws[:50], draws[:100], draws[:300]

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
    mid_avg = sum(score_map.values()) / 45
    mid = sorted(range(1, 46), key=lambda n: (abs(score_map[n] - mid_avg), n))
    sums30 = [sum(d["n"]) for d in recent30] or [135]
    acs30 = [_ac(d["n"]) for d in recent30] or [7]

    cache = {
        "engine_version": ENGINE_VERSION,
        "cache_storage": "database.ai_analysis_cache",
        "created_at": int(time.time()),
        "draw_count": len(draws),
        "latest_round": latest_round,
        "next_round": latest_round + 1,
        "target_round": target,
        "round_range": coverage.get("round_range"),
        "is_full_history": bool(coverage.get("is_full_history")),
        "missing_rounds_count": int(coverage.get("missing_count") or 0),
        "missing_rounds_sample": coverage.get("missing_sample") or [],
        "expected_count": coverage.get("expected_count"),
        "actual_count": coverage.get("actual_count"),
        "analysis_confirm": f"1회차~{target}회차 기준 점검: {'완료' if coverage.get('is_full_history') else '누락 있음'}",
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
        "pair_top": [[list(k), int(v)] for k, v in pair_all.most_common(100)],
        "triple_top": [[list(k), int(v)] for k, v in triple300.most_common(60)],
        "avg_sum30": round(sum(sums30) / len(sums30), 1),
        "avg_ac30": round(sum(acs30) / len(acs30), 1),
        "end_counts": {str(k): int(v) for k, v in Counter(n % 10 for n in _flatten(recent30)).items()},
        "zone_counts": _zones(_flatten(recent30)),
        "latest": draws[0],
    }
    _write_cache_to_db(cache)
    return cache


def _cache_valid(cache: Dict[str, Any], draws: Sequence[Dict[str, Any]], target_round: Optional[int] = None) -> bool:
    if not cache or not draws:
        return False
    latest = max(d["r"] for d in draws)
    target = int(target_round or max(DEFAULT_TARGET_ROUND, latest))
    return (
        int(cache.get("latest_round") or 0) == latest
        and int(cache.get("draw_count") or 0) == len(draws)
        and int(cache.get("target_round") or 0) == target
        and str(cache.get("engine_version")) == ENGINE_VERSION
    )


def get_analysis_cache(force: bool = False, target_round: Optional[int] = None) -> Dict[str, Any]:
    draws = _load_draws()
    if force:
        return _build_cache(target_round)
    cache = _read_cache_from_db()
    if not _cache_valid(cache or {}, draws, target_round):
        return _build_cache(target_round)
    return cache or _build_cache(target_round)


def latest_stats(limit: int = 0) -> Dict[str, Any]:
    c = get_analysis_cache(False)
    return {
        "engine_version": c.get("engine_version", ENGINE_VERSION),
        "cache_storage": c.get("cache_storage"),
        "latest_round": c.get("latest_round", 0),
        "next_round": c.get("next_round", 0),
        "target_round": c.get("target_round", DEFAULT_TARGET_ROUND),
        "draw_count": c.get("draw_count", 0),
        "round_range": c.get("round_range", []),
        "is_full_history": c.get("is_full_history", False),
        "missing_rounds_count": c.get("missing_rounds_count", 0),
        "missing_rounds_sample": c.get("missing_rounds_sample", []),
        "expected_count": c.get("expected_count", 0),
        "actual_count": c.get("actual_count", 0),
        "analysis_confirm": c.get("analysis_confirm"),
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
    avg = sum(smap.values()) / max(1, len(smap))
    weights: Dict[int, float] = {}
    for n in range(1, 46):
        w = 1.0 + (smap.get(n, avg) / max(1.0, avg))
        if n in hot: w += 1.25
        if n in overdue: w += 0.85
        if n in cold: w += 0.45
        if n in mid: w += 0.35
        if mode == "conservative" and 11 <= n <= 35: w += 0.55
        elif mode == "aggressive" and (n <= 12 or n >= 34): w += 0.45
        if grade == "1등": w *= 1.08 if n in hot or n in overdue else 1.0
        elif grade == "2등": w *= 1.04
        weights[n] = max(0.2, w)
    return weights


def _pick(weights: Dict[int, float], banned: set[int]) -> int:
    items = [(n, w) for n, w in weights.items() if n not in banned]
    total = sum(w for _, w in items) or 1.0
    r = random.random() * total
    for n, w in items:
        r -= w
        if r <= 0:
            return n
    return items[-1][0]


def _signature(nums: Sequence[int]) -> Dict[str, Any]:
    nums = sorted(nums)
    odd = sum(n % 2 for n in nums)
    return {"sum": sum(nums), "odd": odd, "even": 6 - odd, "zones": _zones(nums), "ac": _ac(nums), "cons": _consecutive(nums), "end_dup": _end_dup(nums)}


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
    if grade == "1등": s += 4.8
    elif grade == "2등": s += 3.2
    s += ((sum(n * n for n in nums) + sum(nums) * 7) % 31 - 15) * 0.055
    s = round(max(72.0, min(99.1, s)), 1)

    reasons: List[str] = []
    if len(set(nums) & hot): reasons.append(f"최근/누적 상승수 {len(set(nums)&hot)}개 반영")
    if len(set(nums) & overdue): reasons.append(f"미출현 GAP 보정수 {len(set(nums)&overdue)}개 포함")
    if pair_hits: reasons.append(f"동반출현 페어 {pair_hits}개 반영")
    reasons.append(f"홀짝 {sig['odd']}:{sig['even']} · 합계 {sig['sum']} · AC {sig['ac']}")
    return s, reasons[:4], sig


def _valid(nums: Sequence[int]) -> bool:
    sig = _signature(nums)
    if len(set(nums)) != 6: return False
    if sig["odd"] not in (2, 3, 4): return False
    if max(sig["zones"]) > 4 or min(sig["zones"]) == 0: return False
    if sig["sum"] < 85 or sig["sum"] > 200: return False
    if sig["cons"] > 2: return False
    if sig["end_dup"] > 3: return False
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
        details.append({"numbers": nums, "score": score, "ai_score": score, "vip_score": score, "grade": "VIP" if score >= 95 else "PREMIUM" if score >= 91 else "NORMAL", "member_grade": grade, "reason": " / ".join(reasons), "reasons": reasons, "sum": sig["sum"], "odd": sig["odd"], "even": sig["even"], "ac": sig["ac"], "zones": sig["zones"], "engine": ENGINE_VERSION})
        if len(selected) >= count:
            break

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
        "ai_v6_candidates": len(candidates),
        "ai_v6_attempts": attempts,
        "ai_v5_candidates": len(candidates),
        "ai_v5_attempts": attempts,
        "ai_v4_candidates": len(candidates),
        "ai_v4_attempts": attempts,
        "cache_used": True,
        "cache_storage": "database.ai_analysis_cache",
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        "full_history": bool(st.get("is_full_history")),
        "is_full_history": bool(st.get("is_full_history")),
        "missing_rounds_count": st.get("missing_rounds_count", 0),
        "analysis_range": st.get("round_range"),
    })
    return selected[:count], details[:count], st


# ---- 공식 동행복권 API 보강 ----
def _official_fetch(round_no: int, timeout: int = 4) -> Optional[Dict[str, Any]]:
    """동행복권 공식 회차 JSON을 가져온다.
    - 1~1231 전체 동기화를 위해 User-Agent/Referer를 넣고 HTTPS 실패 시 HTTP도 재시도한다.
    - 실패 시 None을 반환하여 누락 회차로 표시한다.
    """
    import urllib.request
    import urllib.parse
    r = int(round_no)
    urls = [
        f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={urllib.parse.quote(str(r))}",
        f"http://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={urllib.parse.quote(str(r))}",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; BBLOTTO-FullHistorySync/1.0)",
                "Accept": "application/json,text/plain,*/*",
                "Referer": "https://www.dhlottery.co.kr/",
            })
            with urllib.request.urlopen(req, timeout=timeout) as res:
                data = json.loads(res.read().decode("utf-8", errors="ignore"))
            if data.get("returnValue") != "success":
                continue
            nums = [int(data[f"drwtNo{i}"]) for i in range(1, 7)]
            bonus = int(data["bnusNo"])
            if len(set(nums)) == 6 and all(1 <= n <= 45 for n in nums) and 1 <= bonus <= 45:
                return {"r": int(data["drwNo"]), "d": str(data.get("drwNoDate") or ""), "n": sorted(nums), "b": bonus}
        except Exception:
            continue
    return None


def _ensure_draws_table() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS draws (
                round_no INTEGER PRIMARY KEY,
                draw_date TEXT DEFAULT '',
                numbers TEXT,
                bonus INTEGER,
                source TEXT DEFAULT 'manual',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _save_draw(draw: Dict[str, Any]) -> None:
    _ensure_draws_table()
    with _conn(DB_PATH) as con:
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


def sync_official_full_history(max_round: Optional[int] = DEFAULT_TARGET_ROUND, stop_after_miss: int = 3) -> Dict[str, Any]:
    """1회차부터 max_round까지 누락분을 공식 API로 보강하고 DB 캐시를 재생성한다.

    RC8.6 핵심 수정:
    - 버튼을 눌렀을 때 상태 확인만 하지 않고 실제로 1~1231 누락 회차를 공식 API에서 내려받아 저장한다.
    - 단일 요청 반복이 느려서 동시 다운로드 방식으로 변경했다.
    - 완료되지 않았는데도 "완료"라고 표시하지 않도록 is_full_history 기준으로 결과를 분리한다.
    """
    before = _load_draws()
    existing = {int(d["r"]) for d in before}
    target = int(max_round or DEFAULT_TARGET_ROUND)
    missing = [r for r in range(MIN_REQUIRED_ROUND, target + 1) if r not in existing]
    saved = 0
    failed_rounds: List[int] = []

    # Railway/Render에서도 너무 오래 걸리지 않도록 동시 요청한다.
    # 환경변수 BBLOTTO_SYNC_WORKERS로 조절 가능, 기본 16개.
    workers = max(1, min(int(os.getenv("BBLOTTO_SYNC_WORKERS", "16") or "16"), 32))
    if missing:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_official_fetch, r): r for r in missing}
            for fut in as_completed(futures):
                r = futures[fut]
                try:
                    d = fut.result()
                except Exception:
                    d = None
                if d:
                    try:
                        _save_draw(d)
                        saved += 1
                        existing.add(int(d["r"]))
                    except Exception:
                        failed_rounds.append(r)
                else:
                    failed_rounds.append(r)

    # max_round를 비워서 호출한 경우에는 최신 회차까지 자동 탐색한다.
    if max_round is None:
        miss = 0
        r = max(existing) + 1 if existing else 1
        while miss < max(1, int(stop_after_miss)):
            d = _official_fetch(r)
            if d:
                _save_draw(d)
                saved += 1
                existing.add(r)
                miss = 0
            else:
                miss += 1
            r += 1

    cache = get_analysis_cache(True, target_round=target)
    is_full = bool(cache.get("is_full_history"))
    missing_count = int(cache.get("missing_rounds_count") or 0)
    return {
        "ok": is_full,
        "completed": is_full,
        "message": (f"1회차~{target}회차 전체 저장/분석 완료" if is_full else f"전체 분석 미완료: {missing_count}개 회차가 아직 누락되었습니다."),
        "requested_range": [1, target],
        "saved": saved,
        "failed": len(failed_rounds),
        "failed_rounds_sample": failed_rounds[:50],
        "draw_count_before": len(before),
        "draw_count_after": cache.get("draw_count"),
        "actual_count": cache.get("actual_count"),
        "expected_count": cache.get("expected_count"),
        "round_range": cache.get("round_range"),
        "latest_round": cache.get("latest_round"),
        "target_round": cache.get("target_round"),
        "is_full_history": is_full,
        "missing_rounds_count": missing_count,
        "missing_rounds_sample": cache.get("missing_rounds_sample"),
        "cache_rebuilt": True,
        "cache_storage": "database.ai_analysis_cache",
        "engine_version": ENGINE_VERSION,
        "source": "dhlottery_official_api",
    }

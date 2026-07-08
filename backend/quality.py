from .draw_service import get_draws


def ac_value(nums):
    diffs = set()
    nums = sorted(nums)
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            diffs.add(abs(nums[j] - nums[i]))
    return max(0, len(diffs) - (len(nums) - 1))


def section_count(nums):
    return [
        len([n for n in nums if 1 <= n <= 15]),
        len([n for n in nums if 16 <= n <= 30]),
        len([n for n in nums if 31 <= n <= 45]),
    ]


def consecutive_pairs(nums):
    nums = sorted(nums)
    return sum(1 for i in range(1, len(nums)) if nums[i] == nums[i - 1] + 1)


def freq_map(limit=100):
    f = {i: 0 for i in range(1, 46)}
    for d in get_draws(limit):
        for n in d.get('n', []):
            if 1 <= n <= 45:
                f[n] += 1
    return f


def evaluate_set(nums):
    nums = sorted([int(n) for n in nums if 1 <= int(n) <= 45])[:6]
    if len(nums) != 6 or len(set(nums)) != 6:
        return {"ok": False, "score": 0, "grade": "오류", "messages": ["번호는 1~45 사이 중복 없는 6개여야 합니다."]}

    f = freq_map(100)
    ranked_hot = sorted(range(1, 46), key=lambda n: (-f[n], n))[:12]
    ranked_cold = sorted(range(1, 46), key=lambda n: (f[n], n))[:12]

    odd = len([n for n in nums if n % 2])
    sec = section_count(nums)
    total = sum(nums)
    ac = ac_value(nums)
    con = consecutive_pairs(nums)
    end_count = len(set(n % 10 for n in nums))
    hot_hit = len([n for n in nums if n in ranked_hot])
    cold_hit = len([n for n in nums if n in ranked_cold])

    score = 100
    messages = []

    if 2 <= odd <= 4:
        messages.append(f"홀짝 {odd}:{6-odd}로 무난합니다.")
    else:
        score -= 12
        messages.append(f"홀짝 {odd}:{6-odd}로 한쪽 비중이 큽니다.")

    if max(sec) <= 3 and min(sec) >= 1:
        messages.append(f"구간 1~15({sec[0]}) / 16~30({sec[1]}) / 31~45({sec[2]})로 분산이 좋습니다.")
    else:
        score -= 14
        messages.append(f"구간 1~15({sec[0]}) / 16~30({sec[1]}) / 31~45({sec[2]})로 일부 몰림이 있습니다.")

    if 90 <= total <= 180:
        messages.append(f"합계 {total}로 일반적인 당첨 범위에 들어옵니다.")
    else:
        score -= 12
        messages.append(f"합계 {total}로 다소 치우친 조합입니다.")

    if 6 <= ac <= 12:
        messages.append(f"AC값 {ac}로 조합 복잡도가 적정합니다.")
    else:
        score -= 10
        messages.append(f"AC값 {ac}로 단순하거나 과분산된 형태입니다.")

    if con <= 1:
        messages.append(f"연속수 {con}쌍으로 부담이 적습니다.")
    else:
        score -= 8
        messages.append(f"연속수 {con}쌍 포함으로 연속 패턴이 강합니다.")

    if end_count >= 5:
        messages.append("끝수 분산이 좋습니다.")
    else:
        score -= 8
        messages.append("같은 끝수 반복이 있어 끝수 분산이 약합니다.")

    if 1 <= hot_hit <= 3:
        messages.append(f"최근 HOT 번호 {hot_hit}개가 포함되어 흐름 반영이 적당합니다.")
    elif hot_hit > 3:
        score -= 5
        messages.append(f"HOT 번호 {hot_hit}개 포함으로 강세수 비중이 높습니다.")
    else:
        score -= 5
        messages.append("HOT 번호 반영이 적어 최근 흐름 연결성이 약합니다.")

    if cold_hit >= 1:
        messages.append(f"COLD/변동 후보 {cold_hit}개가 포함되어 변동성을 보완했습니다.")

    score = max(0, min(100, score))
    grade = "우수" if score >= 86 else "양호" if score >= 75 else "보통" if score >= 60 else "주의"
    return {
        "ok": True,
        "numbers": nums,
        "score": score,
        "grade": grade,
        "odd": odd,
        "even": 6 - odd,
        "sections": sec,
        "sum": total,
        "ac": ac,
        "consecutive": con,
        "end_digit_diversity": end_count,
        "hot_hit": hot_hit,
        "cold_hit": cold_hit,
        "messages": messages,
    }


def evaluate_sets(sets):
    items = [evaluate_set(s) for s in sets]
    scores = [x.get('score', 0) for x in items if x.get('ok')]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    grade = "우수" if avg_score >= 86 else "양호" if avg_score >= 75 else "보통" if avg_score >= 60 else "주의"
    return {"avg_score": avg_score, "grade": grade, "items": items}

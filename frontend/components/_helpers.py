def get_score_color_class(score: float) -> str:
    if score >= 85:
        return "score-optimal"
    elif score >= 70:
        return "score-strong"
    elif score >= 50:
        return "score-moderate"
    else:
        return "score-urgent"

def get_severity_color(level: str) -> str:
    l = level.lower()
    if "critical" in l:
        return "#dc2626"
    elif "warning" in l:
        return "#d97706"
    else:
        return "#2563eb"

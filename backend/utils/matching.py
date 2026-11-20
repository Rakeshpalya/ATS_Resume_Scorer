import re
from typing import List, Dict, Tuple
from rapidfuzz import fuzz

SKILL_ALIASES: Dict[str, str] = {
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node": "node.js",
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "pyspark": "spark",
    "apache spark": "spark",
    "aws": "amazon web services",
    "amazon web services": "aws",
    "gcp": "google cloud platform",
    "google cloud": "google cloud platform",
    "azure": "microsoft azure",
    "ms azure": "microsoft azure",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "ts": "typescript",
    "js": "javascript",
    "py": "python",
    "golang": "go",
    "vuejs": "vue",
    "vue.js": "vue",
    "angularjs": "angular",
    "ci/cd": "cicd",
    "ci-cd": "cicd",
    "machine learning": "ml",
    "artificial intelligence": "ai",
    "deep learning": "dl",
    "natural language processing": "nlp",
    "large language models": "llm",
    "llms": "llm",
    "fastapi": "fastapi",
    "docker containers": "docker",
}

DECORATIVE_CHARS_REGEX = re.compile(r"[│║┌┐└┘├┤┬┴┼─━═║▲▼◆★☆●○▪▫■□▶►◄◄]")
METRICS_PATTERNS = [
    re.compile(r"\b\d+%\b"),
    re.compile(r"\$\s*\d+([,\.]\d+)?\s*([kKmMbB]|million|thousand|billion)?\b"),
    re.compile(r"\b\d+\s*([kKmMbB]|million|billion|thousand)\b", re.IGNORECASE),
    re.compile(r"\b\d+\s*(users|clients|customers|projects|leads|repos|endpoints|microservices|pipelines|teams)\b", re.IGNORECASE),
    re.compile(r"\b(increased|decreased|improved|reduced|grew|boosted|saved|cut|accelerated|scaled)\s+(by\s+)?\d+([,\.]\d+)?%?\b", re.IGNORECASE),
    re.compile(r"\b\d+x\b", re.IGNORECASE)
]

ADDRESS_REGEX = re.compile(
    r"\b\d{1,5}\s+([A-Za-z0-9\.\#\s]{2,25})\s+(Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir)\b",
    re.IGNORECASE
)
ZIP_CODE_REGEX = re.compile(r"\b\d{5}(-\d{4})?\b")

def normalize_skill(skill: str) -> str:
    cleaned = skill.lower().strip()
    cleaned = re.sub(r"[^\w\s\.\+#\-\/]", "", cleaned)
    return SKILL_ALIASES.get(cleaned, cleaned)

def fuzzy_match_skill(query: str, target: str, threshold: int = 80) -> bool:
    norm_q = normalize_skill(query)
    norm_t = normalize_skill(target)
    if norm_q == norm_t:
        return True
    if norm_q in norm_t or norm_t in norm_q:
        return True
    ratio = fuzz.token_sort_ratio(norm_q, norm_t)
    return ratio >= threshold

def extract_measurable_metrics(text: str) -> List[str]:
    matches: List[str] = []
    for pattern in METRICS_PATTERNS:
        for match in pattern.finditer(text):
            matches.append(match.group(0).strip())
    # Deduplicate while preserving order
    return list(dict.fromkeys(matches))

def detect_decorative_characters(text: str) -> List[str]:
    found = DECORATIVE_CHARS_REGEX.findall(text)
    return list(set(found))

def detect_privacy_risks(text: str) -> Tuple[bool, List[str]]:
    risks = []
    street_matches = ADDRESS_REGEX.findall(text)
    if street_matches:
        risks.append("Full street address detected (privacy & ATS parsing risk)")
    zip_matches = ZIP_CODE_REGEX.findall(text)
    if zip_matches:
        risks.append("5-digit postal zip code detected")
    return (len(risks) > 0, risks)

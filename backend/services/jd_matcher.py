import logging
import numpy as np
from typing import List, Tuple, Set, Optional
from sentence_transformers import SentenceTransformer
import spacy

from backend.core.config import settings
from backend.models.schemas import ParsedResume, ParsedJobDescription, JDComparisonResult
from backend.utils.matching import normalize_skill, fuzzy_match_skill

logger = logging.getLogger(__name__)

class JDMatcher:
    def __init__(self):
        self._st_model: Optional[SentenceTransformer] = None
        self._nlp = None

    def get_st_model(self) -> SentenceTransformer:
        if self._st_model is None:
            model_name = settings.SENTENCE_TRANSFORMER_MODEL or "all-MiniLM-L6-v2"
            try:
                self._st_model = SentenceTransformer(model_name)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer '{model_name}': {e}")
        return self._st_model

    def get_nlp(self):
        if self._nlp is None:
            try:
                self._nlp = spacy.load("en_core_web_md")
            except Exception:
                try:
                    self._nlp = spacy.load("en_core_web_sm")
                except Exception:
                    self._nlp = spacy.blank("en")
        return self._nlp

    def compute_semantic_similarity(self, text_a: str, text_b: str) -> float:
        """Computes cosine similarity between two texts using SentenceTransformer."""
        if not text_a.strip() or not text_b.strip():
            return 0.0
        model = self.get_st_model()
        if not model:
            return 0.0

        try:
            emb_a = model.encode(text_a, convert_to_numpy=True)
            emb_b = model.encode(text_b, convert_to_numpy=True)
            norm_a = np.linalg.norm(emb_a)
            norm_b = np.linalg.norm(emb_b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            sim = float(np.dot(emb_a, emb_b) / (norm_a * norm_b))
            return max(0.0, min(1.0, (sim + 1.0) / 2.0 if sim < 0 else sim))
        except Exception as e:
            logger.warning(f"Error computing semantic similarity: {e}")
            return 0.0

    def extract_jd_entities(self, jd_text: str) -> List[str]:
        """Extracts noun chunks and entities from job description text."""
        nlp = self.get_nlp()
        doc = nlp(jd_text[:10000])
        entities = set()
        
        # Named entities
        for ent in doc.ents:
            if ent.label_ in {"ORG", "PRODUCT", "WORK_OF_ART", "LANGUAGE"}:
                cleaned = ent.text.strip().lower()
                if len(cleaned) > 2:
                    entities.add(cleaned)

        # Noun chunks
        if doc.has_annotation("DEP"):
            for chunk in doc.noun_chunks:
                cleaned = chunk.text.strip().lower()
                # filter out pronouns or overly long phrases
                if 2 < len(cleaned) < 35 and not any(w in cleaned for w in ["we", "our", "you", "they", "candidate", "role"]):
                    entities.add(cleaned)

        return list(entities)

    def match(self, resume: ParsedResume, jd: ParsedJobDescription) -> JDComparisonResult:
        """Matches resume with job description and computes match score and missing keywords."""
        if not jd.raw_text and not jd.required_skills and not jd.keywords:
            return JDComparisonResult(match_percentage=100.0, semantic_similarity=1.0)

        # Combine all JD target skills & keywords
        target_skills: Set[str] = set()
        for s in jd.required_skills:
            target_skills.add(s)
        for s in jd.preferred_skills:
            target_skills.add(s)
        for k in jd.keywords:
            target_skills.add(k)

        # Also extract entities from JD text if sparse
        if len(target_skills) < 5 and jd.raw_text:
            extracted = self.extract_jd_entities(jd.raw_text)
            for item in extracted[:15]:
                target_skills.add(item)

        if not target_skills:
            return JDComparisonResult(match_percentage=100.0, semantic_similarity=1.0)

        resume_skills_and_keywords = set(resume.skills + resume.keywords)
        resume_full_text = (resume.raw_text or "").lower()

        matched_keywords: List[str] = []
        missing_keywords: List[str] = []

        for target in target_skills:
            norm_target = normalize_skill(target)
            matched = False

            # Check direct or fuzzy match in resume skills/keywords
            for r_item in resume_skills_and_keywords:
                if fuzzy_match_skill(target, r_item):
                    matched = True
                    break

            # Check substring match in raw text
            if not matched and norm_target in resume_full_text:
                matched = True

            if matched:
                matched_keywords.append(target)
            else:
                missing_keywords.append(target)

        total_targets = len(target_skills)
        match_percentage = (len(matched_keywords) / total_targets * 100.0) if total_targets > 0 else 100.0

        # Semantic similarity
        resume_summary_and_exp = resume.professional_summary + " " + " ".join(e.description for e in resume.experience)
        if not resume_summary_and_exp.strip():
            resume_summary_and_exp = resume.raw_text or ""
        semantic_sim = self.compute_semantic_similarity(resume_summary_and_exp, jd.raw_text or " ".join(target_skills))

        # Skill gaps from required_skills specifically
        skill_gaps: List[str] = []
        for req in jd.required_skills:
            if req in missing_keywords:
                skill_gaps.append(req)

        return JDComparisonResult(
            match_percentage=round(match_percentage, 1),
            semantic_similarity=round(semantic_sim, 2),
            matched_keywords=sorted(list(set(matched_keywords))),
            missing_keywords=sorted(list(set(missing_keywords))),
            skill_gaps=sorted(list(set(skill_gaps)))
        )

jd_matcher = JDMatcher()

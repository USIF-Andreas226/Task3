import json
import os
import re
import difflib
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class KnowledgeBase:
    def __init__(self) -> None:
        self.courses: list[dict[str, Any]] = []
        self.roadmaps: list[dict[str, Any]] = []
        self.markdown_docs: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        courses_path = DATA_DIR / "kayfa_courses.json"
        if courses_path.exists():
            with open(courses_path) as f:
                self.courses = json.load(f)

        roadmaps_path = DATA_DIR / "kayfa_roadmaps.json"
        if roadmaps_path.exists():
            with open(roadmaps_path) as f:
                self.roadmaps = json.load(f)

        for md_file in DATA_DIR.glob("*.md"):
            if md_file.name == "data_summary.md":
                continue
            with open(md_file) as f:
                self.markdown_docs[md_file.stem] = f.read()

    def search_courses(
        self,
        query: str | None = None,
        track: str | None = None,
        level: str | None = None,
        max_price: float | None = None,
        paid_only: bool | None = None,
        free_only: bool | None = None,
    ) -> list[dict[str, Any]]:
        results = list(self.courses)
        if query:
            q = query.lower()
            results = [
                c
                for c in results
                if q in c["name"].lower()
                or q in c["summary"].lower()
                or q in c["track"].lower()
                or q in c.get("skills", "").lower()
            ]
        if track:
            results = [c for c in results if c["track"].lower() == track.lower()]
        if level and level != "All":
            results = [c for c in results if c["level"].lower() == level.lower()]
        if max_price is not None:
            results = [c for c in results if c.get("price", 0) <= max_price]
        if paid_only:
            results = [c for c in results if c.get("paid")]
        if free_only:
            results = [c for c in results if not c.get("paid")]
        return results

    def get_course_by_id(self, course_id: str) -> dict[str, Any] | None:
        for c in self.courses:
            if c["id"] == course_id:
                return c
        return None

    def get_courses_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        return [c for c in self.courses if c["id"] in ids]

    def search_roadmaps(
        self,
        query: str | None = None,
        track: str | None = None,
        roadmap_type: str | None = None,
    ) -> list[dict[str, Any]]:
        results = list(self.roadmaps)
        if query:
            q = query.lower()
            q_words = set(q.split())
            scored: list[tuple[float, dict[str, Any]]] = []
            for r in results:
                score = 0.0
                text = (r["name"] + " " + r.get("track", "") + " " + " ".join(r.get("skills", []))).lower()
                if q in text:
                    score += 3.0
                for w in q_words:
                    if w in text:
                        score += 1.0
                    else:
                        fuzz = self._fuzzy_token_score(w, text)
                        if fuzz > 0:
                            score += fuzz * 0.6
                scored.append((score, r))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [r for s, r in scored if s > 0]
        if track:
            results = [r for r in results if r.get("track", "").lower() == track.lower()]
        if roadmap_type:
            results = [r for r in results if r.get("type") == roadmap_type]
        return results

    def get_roadmap_by_id(self, roadmap_id: str) -> dict[str, Any] | None:
        for r in self.roadmaps:
            if r["id"] == roadmap_id:
                return r
        return None

    def search_markdown(self, query: str) -> list[tuple[str, str, str]]:
        results: list[tuple[str, str, str]] = []
        q = query.lower()
        for doc_name, content in self.markdown_docs.items():
            if q in content.lower():
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if q in line.lower():
                        start = max(0, i - 1)
                        end = min(len(lines), i + 3)
                        snippet = "\n".join(lines[start:end])
                        results.append((doc_name, snippet.strip(), f"{doc_name}:{i+1}"))
        return results

    def get_markdown_doc(self, name: str) -> str | None:
        return self.markdown_docs.get(name)

    def _fuzzy_token_score(self, token: str, text: str, threshold: float = 0.6) -> float:
        text_lower = text.lower()
        if token in text_lower:
            return 1.0
        for word in text_lower.split():
            ratio = difflib.SequenceMatcher(None, token, word).ratio()
            if ratio >= threshold:
                return ratio
        return 0.0

    def semantic_search_courses(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        q = query.lower()
        q_words = set(q.split())
        scored: list[tuple[float, dict[str, Any]]] = []
        for c in self.courses:
            score = 0.0
            text = (c["name"] + " " + c["summary"] + " " + c["track"]).lower()
            if q in text:
                score += 3.0
            for w in q_words:
                if w in text:
                    score += 1.0
                else:
                    fuzz = self._fuzzy_token_score(w, text)
                    if fuzz > 0:
                        score += fuzz * 0.6
                if w in c["name"].lower():
                    score += 2.0
                if w in c["track"].lower():
                    score += 1.5
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for s, c in scored[:top_k] if s > 0]

    def get_recommendations(
        self,
        goal: str | None = None,
        level: str | None = None,
        budget: float | None = None,
    ) -> list[dict[str, Any]]:
        candidates = list(self.courses)
        if level and level != "All":
            candidates = [c for c in candidates if c["level"].lower() == level.lower()]
        if budget is not None:
            candidates = [c for c in candidates if c["price"] <= budget]
        if goal:
            g = goal.lower()
            track_map = {
                "data science": "Data Science",
                "machine learning": "Data Science",
                "ai": "AI",
                "artificial intelligence": "AI",
                "cybersecurity": "Cybersecurity",
                "security": "Cybersecurity",
                "hacking": "Cybersecurity",
                "soc": "Cybersecurity",
                "web development": "Web Development",
                "web dev": "Web Development",
                "frontend": "Web Development",
                "backend": "Web Development",
                "full stack": "Web Development",
                "programming": "Programming",
                "python": "Programming",
                "devops": "DevOps",
                "cloud": "Cloud Computing",
                "mobile": "Mobile Development",
            }
            for keyword, mapped_track in track_map.items():
                if keyword in g:
                    track_candidates = [c for c in candidates if c["track"] == mapped_track]
                    if track_candidates:
                        scored = []
                        for c in track_candidates:
                            s = 0.0
                            if c["level"].lower() == (level or "beginner").lower():
                                s += 2
                            if not c["paid"]:
                                s += 1
                            scored.append((s, c))
                        scored.sort(key=lambda x: x[0], reverse=True)
                        return [c for _, c in scored[:5]]
        candidates.sort(key=lambda c: (0 if not c["paid"] else 1, c["price"]))
        return candidates[:5]


class RAGRetriever:
    def __init__(self, kb: KnowledgeBase | None = None) -> None:
        self.kb = kb or KnowledgeBase()

    def retrieve_context(self, query: str) -> str:
        parts: list[str] = []
        q = query.lower()

        # Always include a summary of available tracks/categories
        parts.append("## الدورات والمسارات المتاحة في كيف")
        available_tracks = set()
        for c in self.kb.courses:
            available_tracks.add(c.get("track", "Unknown"))
        parts.append(f"المسارات المتاحة: {', '.join(sorted(available_tracks))}")
        parts.append("")

        courses = self.kb.semantic_search_courses(query, top_k=5)
        if courses:
            parts.append("## الدورات ذات الصلة بطلبك")
            for c in courses:
                price_str = f"${c['price']}" if c["paid"] else "مجاناً"
                parts.append(
                    f"- **{c['name']}** ({c['track']}, {c['level']}, {c['duration']} ساعة, {price_str}): {c['summary']}"
                )
            parts.append("")

        roadmaps = self.kb.search_roadmaps(query)
        if not roadmaps:
            q_words = set(re.sub(r"[^\w\s]", " ", q).split())
            for r in self.kb.roadmaps:
                name_lower = r["name"].lower()
                for w in q_words:
                    if len(w) > 2 and w in name_lower:
                        roadmaps.append(r)
                        break
        if roadmaps:
            parts.append("## المسارات والدبلومات ذات الصلة")
            for r in roadmaps[:4]:
                rtype = "مباشر" if r.get("type") == "live" else "تسجيلي"
                course_names = []
                for cid in r.get("course_ids", [])[:6]:
                    c = self.kb.get_course_by_id(cid)
                    if c:
                        course_names.append(c["name"])
                parts.append(
                    f"- **{r['name']}** ({rtype}, {r['duration']}, ${r['price']}): مهارات: {', '.join(r.get('skills', [])[:5])}"
                )
                if course_names:
                    parts.append(f"  الدورات المضمنة: {', '.join(course_names)}")
            parts.append("")
        
        # If no specific courses found, show all courses by track to ensure data availability
        if len(courses) < 2:
            q_track = None
            if any(t in q for t in ["ai", "artificial intelligence", "ذكاء"]):
                q_track = "AI"
            elif any(t in q for t in ["security", "cybersecurity", "سيبراني", "أمن"]):
                q_track = "Cybersecurity"
            elif any(t in q for t in ["data science", "data", "بيانات"]):
                q_track = "Data Science"
            elif any(t in q for t in ["web", "development", "backend", "frontend", "تطوير"]):
                q_track = "Web Development"
                
            if q_track:
                track_courses = [c for c in self.kb.courses if c.get("track") == q_track]
                if track_courses and not courses:
                    parts.append(f"## جميع دورات مسار {q_track}")
                    for c in track_courses:
                        price_str = f"${c['price']}" if c["paid"] else "مجاناً"
                        parts.append(
                            f"- **{c['name']}** ({c['level']}, {c['duration']} ساعة, {price_str}): {c['summary']}"
                        )
                    parts.append("")

        diploma_keywords = ["diploma", "دبلوم", "دبلومة", "live", "مباشر"]
        if any(k in q for k in diploma_keywords):
            q_words = set(re.sub(r"[^\w\s]", " ", q).lower().split())
            for doc_name in ["diploma_soc", "diploma_ai", "diploma_data_science", "diploma_pen_test", "diploma_full_stack"]:
                doc = self.kb.get_markdown_doc(doc_name)
                if doc:
                    doc_lower = doc.lower()
                    matched = False
                    for w in q_words:
                        if len(w) > 2 and w in doc_lower:
                            matched = True
                            break
                    for kw in ["soc", "ai", "data science", "penetration", "full stack", "pentest"]:
                        if kw in q and kw in doc_name.lower():
                            matched = True
                            break
                    if matched:
                        lines = doc.split("\n")
                        relevant = "\n".join(lines[:min(60, len(lines))])
                        parts.append(f"## [معلومات الدبلومة: {doc_name}]")
                        parts.append(relevant)
                        parts.append("")

        if "refund" in q or "استرجاع" in q or "استرداد" in q:
            refund_doc = self.kb.get_markdown_doc("kayfa_policies_faqs")
            if refund_doc:
                start = refund_doc.find("## Refund Policy")
                if start >= 0:
                    parts.append("## سياسة الاسترجاع")
                    parts.append(refund_doc[start : start + 1000])

        if len(parts) < 4:
            md_results = self.kb.search_markdown(query)
            if md_results:
                seen: set[str] = set()
                for doc_name, snippet, _ in md_results[:4]:
                    key = f"{doc_name}:{snippet[:40]}"
                    if key not in seen:
                        seen.add(key)
                        parts.append(f"📋 **{doc_name}**: {snippet}")
        
        # Always include company info if context is still sparse
        if len(parts) < 5:
            company_doc = self.kb.get_markdown_doc("kayfa_company_overview")
            if company_doc:
                parts.append("## نبذة عن كيف")
                parts.append(company_doc[:500])

        return "\n".join(parts)

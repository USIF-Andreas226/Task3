# Data Summary — Kayfa Knowledge Base

This document provides a quick reference for how the knowledge base files are organized and how they relate to each other.

## File Structure

| File | Format | Content | Best For |
|------|--------|---------|----------|
| `kayfa_courses.json` | JSON | 52 courses with id, name, summary, track, level, duration, prerequisites, link, price, roadmaps | Structured lookup, search by skill/track/level, filtering |
| `kayfa_roadmaps.json` | JSON | 13 learning paths (10 self-paced, 3 live diplomas) with skills, tools, duration, course count, course IDs, price | Finding the right track/diploma, comparing options |
| `kayfa_company_overview.md` | Markdown | Company info, mission, values, accreditation, key metrics, contacts, team | Identity, credibility, trust-building |
| `kayfa_policies_faqs.md` | Markdown | Refund policy, payment options, certificates, access, tech requirements, support hours, FAQs | Answering practical questions about purchasing |
| `kayfa_privacy_policy.md` | Markdown | Data collection, usage, sharing, protection, rights, retention | Privacy concerns, trust |
| `kayfa_instructors.md` | Markdown | 25 instructors with bios, certifications, experience, teaching subjects, dialects | Social proof, credibility |
| `kayfa_paid_individual_courses.md` | Markdown | All paid courses by category with USD prices, durations, levels | Quick price lookups |
| `kayfa_paid_educational_tracks.md` | Markdown | 10 self-paced tracks with details, prices, installments, links | Track recommendations |
| `kayfa_free_educational_content.md` | Markdown | 6 free courses and free resources | Entry point for hesitant prospects |
| `diploma_ai.md` | Markdown | AI Diploma details, pitch, objection handling, closing | Premium upsell |
| `diploma_data_science.md` | Markdown | Data Science Diploma details, pitch, objection handling, closing | Premium upsell |
| `diploma_soc.md` | Markdown | SOC Diploma details, pitch, objection handling, closing, comparison | Premium upsell |
| `diploma_pen_test.md` | Markdown | Pentesting Diploma details, pitch, objection handling, closing | Premium upsell |
| `diploma_full_stack.md` | Markdown | Full-Stack Diploma details, pitch, objection handling, closing | Premium upsell |

## Data Relationships

### Courses → Tracks
- Each course lists which roadmaps (tracks/diplomas) include it in `roadmaps[]`
- Each track/diploma lists its course IDs in `course_ids[]`

### Tiers (Low → High Value)
1. **Free content** (free courses) — $0 — entry point
2. **Individual courses** — $15 – $65
3. **Self-paced tracks** — $150 – $250
4. **Live diplomas** — $850 – $1,050 — closing target

## How to Reference Data
When the agent needs to answer a question, it should:
1. Search `kayfa_courses.json` for course-specific questions (price, duration, level, prerequisites)
2. Search `kayfa_roadmaps.json` for track/diploma-related questions
3. Search markdown files for policy, FAQ, pricing, and company-related questions
4. Use diploma .md files for persuasive sales conversations and objection handling

## Important Rules
- NEVER invent prices — always check the JSON or paid courses markdown
- NEVER invent courses — only recommend courses from the JSON
- For refund questions, always cite the specific policy from kayfa_policies_faqs.md
- For instructor credibility, reference kayfa_instructors.md
- For company trust, reference kayfa_company_overview.md

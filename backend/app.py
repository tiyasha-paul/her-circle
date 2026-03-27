import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from groq import Groq

from rag import rag_is_ready, retrieve_medical_context
from reddit import fetch_reddit_posts
from scraper import fetch_medical_sources

load_dotenv()

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are Her Circle, a women's reproductive health assistant.
Your job is to give grounded, useful, human-sounding answers about periods, hormones, reproductive health, fertility, contraception, and related symptoms.

You will receive:
1. The user's question
2. The preferred response language
3. Relevant medical source excerpts
4. Relevant Reddit posts from real women

Use the medical sources as the primary grounding. Use Reddit experiences only as lived-experience context, never as medical proof.

Rules:
- Respond in the preferred response language
- Give a real answer, not a generic one-paragraph summary
- Start with a direct answer, then expand with useful nuance, common reasons, what to watch, and practical next steps when helpful
- Make the answer feel thoughtful and specific to the user's question
- Keep the tone calm, clear, non-judgmental, and easy to understand
- Write the answer using light markdown when it helps clarity: short bullet lists, **bold** emphasis, and *italics* sparingly
- When listing causes, warning signs, next steps, or options, prefer bullet points instead of long comma-heavy sentences
- Use at least one small formatting aid in substantive answers: either a short bold lead-in, a short bulleted list, or brief emphasis
- Use short paragraphs with paragraph breaks inside the "answer" string when useful
- Do not force the same structure every time; adapt depth to the question
- Use the provided "Question type" and "Follow-up intent" to shape the answer naturally
- Every substantive paragraph or bullet must be supportable by the provided medical excerpts; if the sources are thin, say so plainly instead of guessing
- If "Question depth" is broad, do not answer briefly. Give a fuller response with:
  1. a direct answer,
  2. common reasons or options,
  3. practical next steps or cautions,
  4. when to seek care if relevant.
- For broad questions, aim for at least 4 useful units of information across short paragraphs or bullets.
- If "Question depth" is focused, you can answer more briefly, but still be specific.
- If Question type is "symptoms", focus on common symptoms, patterns that matter, and what makes symptoms more concerning.
- If Question type is "causes", focus on the most common causes first, then important less-common causes, and what clues help distinguish them.
- If Question type is "what_should_i_do", focus on safe next steps, what not to try blindly, and when professional care matters.
- If Question type is "myth_check", lead with the myth correction, then explain what is true and why the myth is misleading.
- If Question type is "contraception_side_effects", explain what can be normal at first, what is not normal, and when to seek medical advice.
- If Question type is "fertility", focus on timing, common signs, what is and isn't reliable, and when to get evaluated.
- If Question type is "urgent_warning_signs", lead with the seriousness first and make the seek-care guidance very explicit.
- If Follow-up intent is "clarification", answer the exact confusing point first before expanding.
- If Follow-up intent is "challenge", address the contradiction or concern directly and clarify the reasoning calmly.
- If Follow-up intent is "new_subquestion", connect it to the earlier conversation briefly, then answer the new point directly.
- Use the provided "Safety level" and "Scope classification" to decide whether to give a normal answer, a safety-first urgent answer, or a brief redirection.
- If Safety level is "emergency", do not give routine self-management advice first. Lead with urgent in-person care guidance immediately.
- If Safety level is "urgent", make the seek-care guidance especially explicit and do not bury it at the end.
- If Scope classification is "clearly_out_of_scope", do not improvise medical content. Briefly say Her Circle focuses on women's reproductive health and ask the user to rephrase in that area.
- Only include medical sources you actually used, and use as many or as few as the answer genuinely needs
- If multiple good sources are available, prefer a mix of organizations instead of listing the same source repeatedly
- Use inline citation markers in the answer when medical claims are supported, using the same numbering as the "sources" array, for example [1] or [1][2]
- Keep citation markers brief and only use them for medical-source support, not for Reddit context
- If Reddit experiences are relevant, weave a brief lived-experience synthesis directly into the answer in plain language
- Summarize Reddit experiences only when they add real value; if not, return an empty array
- If the question contains a myth or misconception, debunk it in the "myth" field; otherwise return null
- If the user should seek medical care, explain when in "see_doctor_if"; otherwise return null
- If the question is unrelated to women's reproductive health, briefly say that Her Circle only handles that topic and ask the user to rephrase; in that case return empty arrays and null optional fields
- If the question asks for dangerous, illegal, self-harm, or deliberately harmful advice, refuse briefly and direct the user to urgent local professional help if safety is at risk
- Return ONLY valid JSON, no prose outside JSON, no markdown backticks

JSON format:
{
  "answer": "A direct, fuller answer with paragraph breaks when helpful.",
  "sources": [{"name": "source title", "url": "real url"}],
  "reddit_experiences": [{"summary": "brief grounded experience summary", "url": "reddit url"}],
  "myth": "myth correction or null",
  "see_doctor_if": "when to seek care or null"
}
"""

JSON_REPAIR_PROMPT = """Convert the following model output into valid JSON.

Rules:
- Preserve the meaning
- Return only valid JSON
- Do not add commentary
- Use this schema exactly:
{
  "answer": "string",
  "sources": [{"name": "string", "url": "string"}],
  "reddit_experiences": [{"summary": "string", "url": "string"}],
  "myth": "string or null",
  "see_doctor_if": "string or null"
}
"""

SEARCH_REWRITE_PROMPT = """Rewrite the user's health question into a short English retrieval query for trusted medical sources.

Rules:
- Preserve the core meaning
- Translate to English if the question is in another language
- Remove filler words
- Keep symptom and topic details
- Keep it under 12 words
- Return plain text only
"""

ANSWER_EXPANSION_PROMPT = """You are revising a draft answer from Her Circle.

Goal:
- Turn a too-short draft into a fuller, more helpful answer
- Keep the same language as the draft/question
- Stay grounded in the provided medical excerpts

Rules:
- Start with a direct answer
- Use short paragraphs or bullet points when helpful
- For broad questions, include at least:
  1. a direct answer,
  2. common reasons or options,
  3. practical next steps or cautions,
  4. when to seek care if relevant
- Do not invent facts not supported by the excerpts
- Keep the tone calm, clear, and non-judgmental
- Return only the revised answer text, not JSON
"""

HARMFUL_TERMS = {
    "kill myself",
    "suicide",
    "hurt myself",
    "self harm",
    "poison",
    "harm someone",
    "abort at home",
    "unsafe abortion",
}

REPRODUCTIVE_TERMS = {
    "period",
    "periods",
    "menstrual",
    "bleeding",
    "clot",
    "clots",
    "pcos",
    "pcod",
    "endo",
    "endometriosis",
    "fibroid",
    "fibroids",
    "hormone",
    "hormones",
    "ovulation",
    "fertility",
    "pregnant",
    "pregnancy",
    "contraception",
    "birth control",
    "iud",
    "implant",
    "pill",
    "pmdd",
    "pms",
    "pelvic",
    "uterus",
    "ovary",
    "ovaries",
    "vaginal",
    "vagina",
    "discharge",
    "itching",
    "rash",
    "amenorrhea",
    "cramps",
    "cervix",
}

OUT_OF_SCOPE_TERMS = {
    "weather",
    "temperature",
    "stock",
    "stocks",
    "bitcoin",
    "crypto",
    "match",
    "football",
    "cricket",
    "nba",
    "movie",
    "song",
    "recipe",
    "capital of",
    "president",
    "prime minister",
    "python code",
    "javascript",
    "java code",
    "bug in my code",
    "leetcode",
    "sql query",
    "homework",
}

EMERGENCY_PATTERNS = (
    "pregnant and bleeding",
    "pregnancy and bleeding",
    "soaking through",
    "soaking a pad",
    "soaking pads",
    "bleeding through",
    "passing out",
    "fainted",
    "fainting",
    "severe pelvic pain",
    "severe abdominal pain",
    "extreme pelvic pain",
    "one sided pain",
    "one-sided pain",
)

LANGUAGE_HINT_PATTERN = re.compile(r"\s*\(respond in ([^)]+)\)\s*$", re.IGNORECASE)
CLARIFICATION_PATTERNS = (
    "explain this part",
    "explain that part",
    "more clearly",
    "what do you mean",
    "what does that mean",
    "can you clarify",
    "clarify this",
    "clarify that",
)

BROAD_QUESTION_PATTERNS = (
    "how can i",
    "how do i",
    "what should i do",
    "what can i do",
    "why is",
    "why am i",
    "how to",
    "can i make",
    "is it normal",
    "what are the signs",
    "what causes",
)

URGENT_PATTERNS = (
    "severe pain",
    "heavy bleeding",
    "soaking",
    "fainting",
    "fever",
    "pregnant and bleeding",
    "can't stand",
    "extreme pain",
    "dizzy",
    "dizziness",
)

CHALLENGE_PATTERNS = (
    "are you sure",
    "that does not make sense",
    "that doesn't make sense",
    "but you said",
    "you said earlier",
    "i thought you said",
    "that seems wrong",
)

SUBQUESTION_PATTERNS = (
    "what if",
    "what about",
    "also",
    "and if",
    "in that case",
    "does that mean",
)

NON_LATIN_PATTERN = re.compile(r"[^\u0000-\u007F]")
LIST_REQUEST_PATTERNS = (
    "list only",
    "give me a list",
    "just list",
    "only list",
    "bullet points only",
    "in points",
    "pointwise",
)
GREETING_PATTERNS = (
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "thanks",
    "thank you",
)


def _build_context(medical_sources, reddit_posts):
    context_lines = ["MEDICAL SOURCES:"]
    if medical_sources:
        for source in medical_sources:
            excerpt = source.get("excerpt") or "No excerpt available."
            context_lines.append(f"- Source: {source['source']}")
            context_lines.append(f"  Title: {source['title']}")
            context_lines.append(f"  URL: {source['url']}")
            context_lines.append(f"  Excerpt: {excerpt}")
    else:
        context_lines.append("- No medical sources were found for this query.")

    context_lines.append("")
    context_lines.append("REDDIT EXPERIENCES:")
    if reddit_posts:
        for post in reddit_posts:
            context_lines.append(
                f"- r/{post['subreddit']}: {post['title']}. {post['body']} ({post['url']})"
            )
    else:
        context_lines.append("- No Reddit experiences were found for this query.")

    return "\n".join(context_lines)


def _build_history_context(history):
    if not history:
        return "No previous conversation."

    history_lines = []
    for item in history[-8:]:
        role = item.get("role", "").strip().lower()
        content = (item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        history_lines.append(f"{role.upper()}: {content}")

    return "\n".join(history_lines) if history_lines else "No previous conversation."


def _extract_recent_topic(history):
    for item in reversed(history or []):
        if item.get("role") != "user":
            continue
        content = (item.get("content") or "").strip()
        if content:
            return content
    return ""


def _extract_requested_language(question):
    match = LANGUAGE_HINT_PATTERN.search(question)
    if not match:
        return question.strip(), None

    language = match.group(1).strip()
    cleaned_question = LANGUAGE_HINT_PATTERN.sub("", question).strip()
    return cleaned_question, language


def _rewrite_search_query(question):
    if NON_LATIN_PATTERN.search(question):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SEARCH_REWRITE_PROMPT},
                    {"role": "user", "content": question},
                ],
                temperature=0,
            )
            rewritten = response.choices[0].message.content.strip()
            if rewritten:
                return rewritten
        except Exception:
            pass

    cleaned = question.lower().strip()
    cleaned = re.sub(r"[^\w\s]", " ", cleaned, flags=re.UNICODE)
    cleaned = re.sub(
        r"\b(can you|please|tell me about|explain|respond|answer|help me understand|what does|mean)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or question


def _is_clarification_follow_up(question):
    lowered = question.lower()
    return any(pattern in lowered for pattern in CLARIFICATION_PATTERNS)


def _looks_like_ambiguous_follow_up(question, history):
    if not history:
        return False

    lowered = question.lower().strip()
    if len(lowered.split()) > 8:
        return False

    follow_up_markers = ("this", "that", "it", "those", "these", "more", "why", "how", "what about")
    return any(marker in lowered for marker in follow_up_markers)


def _question_depth_hint(question):
    lowered = question.lower().strip()
    if any(pattern in lowered for pattern in BROAD_QUESTION_PATTERNS):
        return "broad"
    if len(lowered.split()) >= 7:
        return "broad"
    return "focused"


def _wants_list_response(question):
    lowered = question.lower().strip()
    return any(pattern in lowered for pattern in LIST_REQUEST_PATTERNS)


def _is_greeting_or_smalltalk(question):
    lowered = re.sub(r"[^\w\s]", " ", question.lower()).strip()
    compact = re.sub(r"\s+", " ", lowered)
    if compact in GREETING_PATTERNS:
        return True
    if len(compact.split()) <= 3 and any(compact.startswith(pattern) for pattern in GREETING_PATTERNS):
        return True
    return False


def _is_low_information_input(question, history):
    lowered = question.lower().strip()
    tokens = re.findall(r"[a-z0-9']+", lowered)

    if not tokens:
        return True

    if _looks_like_ambiguous_follow_up(question, history):
        return False

    if any(term in lowered for term in REPRODUCTIVE_TERMS):
        return False

    if any(term in lowered for term in OUT_OF_SCOPE_TERMS):
        return False

    if re.match(r"^(who|what|when|where|why|how|is|are|am|can|could|should|would|do|does|did|will)\b", lowered):
        return False

    if len(tokens) == 1:
        token = tokens[0]
        if len(token) <= 3:
            return True
        if re.fullmatch(r"[bcdfghjklmnpqrstvwxyz]+", token):
            return True

    if len(tokens) <= 2 and not question.endswith("?"):
        return True

    return False


def _classify_question_type(question):
    lowered = question.lower().strip()

    if any(pattern in lowered for pattern in URGENT_PATTERNS):
        return "urgent_warning_signs"
    if any(pattern in lowered for pattern in CLARIFICATION_PATTERNS):
        return "clarification"
    if "myth" in lowered or lowered.startswith("is it true") or lowered.startswith("can ") and "stop periods" in lowered:
        return "myth_check"
    if any(term in lowered for term in ("birth control", "pill", "iud", "implant", "shot", "emergency contraception", "morning after")):
        return "contraception_side_effects"
    if any(term in lowered for term in ("fertility", "ovulation", "conceive", "pregnant", "pregnancy", "trying to get pregnant")):
        return "fertility"
    if "signs" in lowered or "symptoms" in lowered or lowered.startswith("do i have"):
        return "symptoms"
    if any(pattern in lowered for pattern in ("why", "cause", "causes", "reason")):
        return "causes"
    if any(pattern in lowered for pattern in ("how can i", "how do i", "what should i do", "what can i do", "how to")):
        return "what_should_i_do"
    return "general"


def _classify_follow_up_intent(question, history):
    user_turns = [item for item in history if item.get("role") == "user" and item.get("content")]
    if not user_turns:
        return "new_question"

    lowered = question.lower().strip()
    if any(pattern in lowered for pattern in CLARIFICATION_PATTERNS):
        return "clarification"
    if any(pattern in lowered for pattern in CHALLENGE_PATTERNS):
        return "challenge"
    if any(pattern in lowered for pattern in SUBQUESTION_PATTERNS):
        return "new_subquestion"
    if _looks_like_ambiguous_follow_up(question, history):
        return "new_subquestion"
    return "new_question"


def _scope_classification(question, history):
    lowered = question.lower().strip()

    if _is_greeting_or_smalltalk(question):
        return "smalltalk"

    if _looks_like_ambiguous_follow_up(question, history):
        return "likely_in_scope_follow_up"

    if any(term in lowered for term in REPRODUCTIVE_TERMS):
        return "in_scope"

    if any(term in lowered for term in OUT_OF_SCOPE_TERMS):
        return "clearly_out_of_scope"

    if re.match(r"^(who|what|when|where)\s", lowered) and not any(term in lowered for term in REPRODUCTIVE_TERMS):
        return "possibly_out_of_scope"

    return "in_scope"


def _safety_level(question):
    lowered = question.lower().strip()

    if any(pattern in lowered for pattern in EMERGENCY_PATTERNS):
        return "emergency"

    if (
        ("heavy bleeding" in lowered and any(term in lowered for term in ("dizzy", "dizziness", "faint", "fainted", "severe pain")))
        or ("fever" in lowered and any(term in lowered for term in ("pelvic pain", "discharge", "bleeding")))
        or ("pregnant" in lowered and any(term in lowered for term in ("pain", "bleeding", "cramping")))
    ):
        return "emergency"

    if any(pattern in lowered for pattern in URGENT_PATTERNS):
        return "urgent"

    return "normal"


def _build_answer_plan(question_type, follow_up_intent, depth_hint):
    plan = []

    if follow_up_intent == "clarification":
        plan.append("Start by answering the exact confusing point in 1 to 2 direct sentences before expanding.")
    elif follow_up_intent == "challenge":
        plan.append("Address the user's concern or contradiction directly before explaining the reasoning.")
    elif follow_up_intent == "new_subquestion":
        plan.append("Briefly connect to the previous answer, then answer the new sub-question directly.")

    if question_type == "symptoms":
        plan.extend(
            [
                "Cover the most common symptoms or patterns first.",
                "Point out which symptom combinations matter more clinically.",
                "Mention what would make the symptoms more concerning.",
            ]
        )
    elif question_type == "causes":
        plan.extend(
            [
                "Lead with the most common causes or explanations.",
                "Then mention important less-common causes only if they are supported by the excerpts.",
                "Add practical clues that help distinguish between likely causes.",
            ]
        )
    elif question_type == "what_should_i_do":
        plan.extend(
            [
                "Give safe, concrete next steps the user can consider.",
                "Say clearly what should not be tried blindly if relevant.",
                "Explain when professional care matters.",
            ]
        )
    elif question_type == "myth_check":
        plan.extend(
            [
                "Start with a direct myth correction.",
                "Explain what is actually true.",
                "Briefly explain why the myth is misleading.",
            ]
        )
    elif question_type == "contraception_side_effects":
        plan.extend(
            [
                "Explain what can be expected or common at first.",
                "Separate that from symptoms that are not expected.",
                "Make the seek-care threshold clear.",
            ]
        )
    elif question_type == "fertility":
        plan.extend(
            [
                "Explain the most useful signs, timing, or cycle clues first.",
                "Mention what is less reliable or easy to misread.",
                "Clarify when evaluation is worth considering.",
            ]
        )
    elif question_type == "urgent_warning_signs":
        plan.extend(
            [
                "Lead with the seriousness of the warning signs.",
                "State what the user should do now in clear language.",
                "Keep the advice direct and safety-focused.",
            ]
        )
    else:
        plan.append("Answer directly first, then add the most useful supporting detail for this specific question.")

    if depth_hint == "broad":
        plan.append("Use at least four useful units of information across short paragraphs or bullet points.")
    else:
        plan.append("Keep the answer concise but still specific and useful.")

    return "\n".join(f"- {item}" for item in plan)


def _format_as_bullets(answer):
    text = (answer or "").strip()
    if not text:
        return text

    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    if not blocks:
        return text

    bullet_lines = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if any(re.match(r"^([-*]|\d+\.)\s+", line) for line in lines):
            for line in lines:
                if re.match(r"^([-*]|\d+\.)\s+", line):
                    bullet_lines.append(re.sub(r"^(\d+\.\s+|[-*]\s+)", "- ", line))
                else:
                    bullet_lines.append(f"- {line}")
            continue

        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", block)
        compact_sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
        if len(compact_sentences) > 1:
            bullet_lines.extend(f"- {sentence}" for sentence in compact_sentences)
        else:
            bullet_lines.append(f"- {block}")

    return "\n".join(bullet_lines)


def _build_grounding_instructions(medical_sources):
    if not medical_sources:
        return (
            "Grounding instructions:\n"
            "- No strong medical excerpts were retrieved.\n"
            "- Be transparent about uncertainty.\n"
            "- Do not invent causes, treatments, timelines, or safety claims.\n"
            "- If the evidence is thin, say that clearly and keep the advice cautious."
        )

    source_names = []
    for source in medical_sources:
        source_name = source.get("source", "").strip()
        if source_name and source_name not in source_names:
            source_names.append(source_name)

    source_list = ", ".join(source_names[:4])
    return (
        "Grounding instructions:\n"
        f"- The retrieved evidence comes from: {source_list}.\n"
        "- Base each substantive paragraph or bullet on the retrieved excerpts.\n"
        "- Prefer the most specific excerpted pages over generic background pages.\n"
        "- If you mention a cause, option, warning sign, or next step, it must be supportable by the excerpts.\n"
        "- If the excerpts do not support a claim strongly, say that the evidence here is limited."
    )


def _format_support_text(value):
    text = (value or "").strip()
    if not text:
        return None

    text = re.sub(r"\s+", " ", text)
    if text and text[0].isalpha():
        text = text[0].upper() + text[1:]
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _useful_unit_count(answer):
    blocks = [block.strip() for block in re.split(r"\n\s*\n", answer or "") if block.strip()]
    count = 0
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if any(line.startswith(("- ", "* ", "1. ", "2. ", "3. ")) for line in lines):
            count += len(lines)
        else:
            count += 1
    return count


def _needs_answer_expansion(answer, depth_hint, question_type, safety_level):
    clean = (answer or "").strip()
    if not clean:
        return False
    if safety_level == "emergency":
        return False
    if depth_hint != "broad" and question_type not in {"causes", "what_should_i_do", "symptoms"}:
        return False
    if len(clean) < 420:
        return True
    if _useful_unit_count(clean) < 4:
        return True
    return False


def _expand_answer_if_needed(answer, question, preferred_language, depth_hint, question_type, safety_level, medical_sources):
    if not _needs_answer_expansion(answer, depth_hint, question_type, safety_level):
        return answer
    if not medical_sources:
        return answer

    evidence_lines = []
    for source in medical_sources[:4]:
        excerpt = source.get("excerpt") or "No excerpt available."
        evidence_lines.append(
            f"- {source['source']}: {source['title']} | {excerpt}"
        )

    prompt = (
        f"Question: {question}\n"
        f"Preferred language: {preferred_language}\n"
        f"Question depth: {depth_hint}\n"
        f"Question type: {question_type}\n"
        f"Safety level: {safety_level}\n\n"
        f"List-only requested: {'yes' if _wants_list_response(question) else 'no'}\n\n"
        f"Current draft answer:\n{answer}\n\n"
        f"Medical evidence:\n" + "\n".join(evidence_lines)
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": ANSWER_EXPANSION_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        revised = response.choices[0].message.content.strip()
        return revised or answer
    except Exception:
        return answer


def _has_inline_citations(answer):
    return bool(re.search(r"\[\d+\]", answer or ""))


def _append_inline_citations(answer, sources):
    if not answer or not sources or _has_inline_citations(answer):
        return answer

    source_count = len(sources)
    blocks = [block.strip() for block in re.split(r"\n\s*\n", answer) if block.strip()]
    if not blocks:
        return answer

    cited_blocks = []
    for index, block in enumerate(blocks):
        marker_index = min(index + 1, source_count)
        marker = f"[{marker_index}]"
        if source_count >= 2 and index == 0:
            marker = "[1][2]"

        lines = block.splitlines()
        updated_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if re.search(r"\[\d+\]", stripped):
                updated_lines.append(line)
                continue
            if re.match(r"^([-*]|\d+\.)\s+", stripped):
                updated_lines.append(f"{line} {marker}")
            else:
                updated_lines.append(f"{line} {marker}")
        cited_blocks.append("\n".join(updated_lines))

    return "\n\n".join(cited_blocks)


def _should_replace_source_name(name, fallback_source):
    cleaned_name = (name or "").strip().lower()
    fallback_source_name = (fallback_source.get("source") or "").strip().lower()
    fallback_title = (fallback_source.get("title") or "").strip().lower()

    if not cleaned_name:
        return True
    if cleaned_name in {fallback_source_name, fallback_title, (fallback_source.get("url") or "").strip().lower()}:
        return True
    if cleaned_name in {
        "office on women's health",
        "acog",
        "medlineplus",
        "cleveland clinic",
        "mayo clinic",
        "nhs",
    }:
        return True
    return False


def _normalize_sources(raw_sources, fallback_sources, is_out_of_scope_answer):
    normalized_sources = raw_sources or []
    allowed_urls = {source["url"] for source in fallback_sources}
    fallback_by_url = {source["url"]: source for source in fallback_sources}

    if not normalized_sources and fallback_sources and not is_out_of_scope_answer:
        normalized_sources = [
            {
                "name": f"{source['source']}: {source['title']}",
                "url": source["url"],
            }
            for source in fallback_sources
        ]

    unique_sources = []
    seen_urls = set()
    for source in normalized_sources:
        url = (source.get("url") or "").strip()
        name = (source.get("name") or "").strip()
        if not url or url in seen_urls:
            continue
        if allowed_urls and url not in allowed_urls:
            continue
        if not allowed_urls:
            continue
        fallback_source = fallback_by_url.get(url)
        if fallback_source and _should_replace_source_name(name, fallback_source):
            name = f"{fallback_source['source']}: {fallback_source['title']}"
        seen_urls.add(url)
        unique_sources.append({"name": name or url, "url": url})

    if len(unique_sources) < 2 and fallback_sources and not is_out_of_scope_answer:
        for source in fallback_sources:
            url = source.get("url", "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            unique_sources.append(
                {
                    "name": f"{source['source']}: {source['title']}",
                    "url": url,
                }
            )
            if len(unique_sources) >= min(3, len(fallback_sources)):
                break

    return unique_sources


def _merge_medical_sources(primary_sources, fallback_sources, limit=6):
    merged = []
    seen_urls = set()

    for source in (primary_sources or []) + (fallback_sources or []):
        url = source.get("url", "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        merged.append(source)
        if len(merged) >= limit:
            break

    return merged


def _retrieve_context(retrieval_query, is_clarification_follow_up, scope_classification, safety_level):
    if scope_classification in {"clearly_out_of_scope", "smalltalk"}:
        return [], []

    if is_clarification_follow_up:
        rag_sources = retrieve_medical_context(retrieval_query, limit=5) if rag_is_ready() else []
        return rag_sources, []

    rag_sources = retrieve_medical_context(retrieval_query, limit=5) if rag_is_ready() else []
    should_fetch_live_sources = len(rag_sources) < 3

    if safety_level in {"urgent", "emergency"}:
        live_sources = fetch_medical_sources(retrieval_query) if should_fetch_live_sources else []
        medical_sources = _merge_medical_sources(rag_sources, live_sources, limit=6)
        return medical_sources, []

    with ThreadPoolExecutor(max_workers=2) as executor:
        reddit_future = executor.submit(fetch_reddit_posts, retrieval_query, 5)
        live_future = executor.submit(fetch_medical_sources, retrieval_query) if should_fetch_live_sources else None

        reddit_posts = reddit_future.result()
        live_sources = live_future.result() if live_future else []

    medical_sources = _merge_medical_sources(rag_sources, live_sources, limit=6)
    return medical_sources, reddit_posts


def _normalize_reddit_experiences(raw_experiences, fallback_posts):
    normalized = raw_experiences or []

    if not normalized and fallback_posts:
        normalized = [
            {
                "summary": _fallback_reddit_summary(post),
                "url": post["url"],
            }
            for post in fallback_posts[:2]
        ]

    unique = []
    seen_urls = set()
    for experience in normalized:
        url = (experience.get("url") or "").strip()
        summary = (experience.get("summary") or "").strip()
        if not url or not summary or url in seen_urls:
            continue
        seen_urls.add(url)
        unique.append({"summary": summary, "url": url})

    return unique


def _fallback_reddit_summary(post):
    subreddit = post.get("subreddit", "Reddit")
    title = (post.get("title") or "").strip().rstrip(".")
    body = (post.get("body") or "").strip()

    if body:
        return f"In r/{subreddit}, one discussion described {title.lower()}: {body}"
    return f"In r/{subreddit}, one discussion focused on {title.lower()}."


def _normalize_response(parsed, medical_sources, reddit_posts, question_context):
    answer = parsed.get("answer", "").strip()
    normalized_reddit = _normalize_reddit_experiences(parsed.get("reddit_experiences"), reddit_posts)

    out_of_scope_markers = (
        "only handles questions related to women's reproductive health",
        "only handles that topic",
        "question seems unrelated",
        "please rephrase your question",
        "ask about periods, hormones",
    )
    is_out_of_scope_answer = any(marker in answer.lower() for marker in out_of_scope_markers)

    normalized_sources = _normalize_sources(parsed.get("sources"), medical_sources, is_out_of_scope_answer)
    answer = _expand_answer_if_needed(
        answer,
        question_context["question"],
        question_context["preferred_language"],
        question_context["depth_hint"],
        question_context["question_type"],
        question_context["safety_level"],
        medical_sources,
    )
    if question_context["wants_list_response"]:
        answer = _format_as_bullets(answer)
    answer = _append_inline_citations(answer, normalized_sources)

    return {
        "answer": answer,
        "sources": normalized_sources,
        "reddit_experiences": [] if is_out_of_scope_answer else normalized_reddit,
        "myth": _format_support_text(parsed.get("myth")),
        "see_doctor_if": _format_support_text(parsed.get("see_doctor_if")),
    }


def _request_groq_json(full_prompt):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": full_prompt},
    ]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
    except Exception:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
        )

    raw = response.choices[0].message.content.strip()
    return _parse_model_json(raw)


def _try_load_json(candidate):
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _repair_json_with_model(raw_text):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": JSON_REPAIR_PROMPT},
                {"role": "user", "content": raw_text},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        repaired = response.choices[0].message.content.strip()
        parsed = _try_load_json(repaired)
        if parsed is not None:
            return parsed
    except Exception:
        return None

    return None


def _parse_model_json(raw_text):
    clean = raw_text.strip().removeprefix("```json").removesuffix("```").strip()

    direct = _try_load_json(clean)
    if direct is not None:
        return direct

    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end != -1 and end > start:
        extracted = clean[start : end + 1]
        parsed = _try_load_json(extracted)
        if parsed is not None:
            return parsed

    repaired = _repair_json_with_model(clean)
    if repaired is not None:
        return repaired

    raise json.JSONDecodeError("Unable to parse model JSON", clean, 0)


def _is_harmful(question):
    lowered = question.lower()
    return any(term in lowered for term in HARMFUL_TERMS)


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    history = data.get("history") or []

    if not question:
        return jsonify({"error": "No question provided"}), 400

    clean_question, requested_language = _extract_requested_language(question)

    if _is_harmful(clean_question):
        return (
            jsonify(
                {
                    "answer": "I can't help with dangerous or self-harm instructions. If someone may be in immediate danger, contact local emergency services or an urgent mental health professional right now.",
                    "sources": [],
                    "reddit_experiences": [],
                    "myth": None,
                    "see_doctor_if": "You or someone else may be at immediate risk, or you need urgent medical help.",
                }
            ),
            200,
        )

    if _is_greeting_or_smalltalk(clean_question):
        return (
            jsonify(
                {
                    "answer": "Hello. I can help with questions about periods, hormones, fertility, contraception, pelvic pain, and related reproductive health concerns. Ask me a specific question whenever you're ready.",
                    "sources": [],
                    "reddit_experiences": [],
                    "myth": None,
                    "see_doctor_if": None,
                }
            ),
            200,
        )

    if _is_low_information_input(clean_question, history):
        return (
            jsonify(
                {
                    "answer": "That message does not look like a clear question yet. Ask a specific question about periods, hormones, fertility, contraception, pelvic pain, or another reproductive health concern, and I'll answer directly.",
                    "sources": [],
                    "reddit_experiences": [],
                    "myth": None,
                    "see_doctor_if": None,
                }
            ),
            200,
        )

    try:
        recent_topic = _extract_recent_topic(history)
        is_clarification_follow_up = _is_clarification_follow_up(clean_question)
        scope_classification = _scope_classification(clean_question, history)
        safety_level = _safety_level(clean_question)
        should_anchor_to_recent_topic = (
            is_clarification_follow_up
            or scope_classification == "likely_in_scope_follow_up"
        )
        retrieval_seed = clean_question if not should_anchor_to_recent_topic else f"{recent_topic} {clean_question}".strip()
        retrieval_query = _rewrite_search_query(retrieval_seed)
        medical_sources, reddit_posts = _retrieve_context(
            retrieval_query,
            is_clarification_follow_up,
            scope_classification,
            safety_level,
        )
        if not medical_sources and scope_classification != "clearly_out_of_scope":
            backup_sources = fetch_medical_sources(clean_question)
            medical_sources = _merge_medical_sources(medical_sources, backup_sources, limit=6)
        classification_text = retrieval_query if NON_LATIN_PATTERN.search(clean_question) else clean_question

        preferred_language = (
            requested_language
            or "same as the user's latest message; if that message is ambiguous, keep the language used earlier in the conversation"
        )
        depth_hint = _question_depth_hint(classification_text)
        wants_list_response = _wants_list_response(clean_question)
        question_type = _classify_question_type(classification_text)
        follow_up_intent = _classify_follow_up_intent(clean_question, history)
        answer_plan = _build_answer_plan(question_type, follow_up_intent, depth_hint)
        grounding_instructions = _build_grounding_instructions(medical_sources)
        full_prompt = (
            f"Conversation so far:\n{_build_history_context(history)}\n\n"
            f"Question: {clean_question}\n"
            f"Preferred response language: {preferred_language}\n"
            f"Question depth: {depth_hint}\n"
            f"Question type: {question_type}\n"
            f"Follow-up intent: {follow_up_intent}\n"
            f"Safety level: {safety_level}\n"
            f"Scope classification: {scope_classification}\n"
            f"List-only requested: {'yes' if wants_list_response else 'no'}\n"
            f"Search query used for retrieval: {retrieval_query}\n\n"
            f"Answer plan:\n{answer_plan}\n\n"
            f"{grounding_instructions}\n\n"
            f"Context:\n{_build_context(medical_sources, reddit_posts)}"
        )
        parsed = _request_groq_json(full_prompt)
        question_context = {
            "question": clean_question,
            "preferred_language": preferred_language,
            "depth_hint": depth_hint,
            "question_type": question_type,
            "safety_level": safety_level,
            "wants_list_response": wants_list_response,
        }

        return jsonify(_normalize_response(parsed, medical_sources, reddit_posts, question_context))
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse AI response"}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "rag_ready": rag_is_ready()})


if __name__ == "__main__":
    app.run(debug=True, port=5000)

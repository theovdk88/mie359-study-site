#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


SITE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SITE_DIR.parent
BUNDLE_DIR = PROJECT_DIR / "mie359_codex_bundle"
MANIFEST_PATH = BUNDLE_DIR / "manifest.json"
DATA_DIR = SITE_DIR / "data"
SITE_JSON_PATH = DATA_DIR / "site.json"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BOLD_DEFINITION_RE = re.compile(r"^\*\*([^*]*definition[^*]*)\*\*\s*(.*)$", re.IGNORECASE)
ORDERED_ITEM_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")
UNORDERED_ITEM_RE = re.compile(r"^\s*[-*]\s+(.*)$")
GENERIC_TITLES = {
    "chapter overview",
    "overview",
    "definition",
    "explanation",
    "main elements of organizational design",
    "characteristics",
    "purpose",
    "mechanisms",
    "forms",
    "common forms",
    "benefits",
    "advantages",
    "disadvantages",
    "limitations",
    "main ideas",
    "core idea",
    "key distinction",
    "quick contrast",
    "why this matters",
    "important implication",
    "important idea",
    "key insight",
    "implication",
    "examples",
    "example",
    "reasons include",
    "challenges",
    "components",
    "stages",
    "main sources",
    "achieved through",
    "forms",
}
FRAMEWORK_KEYWORDS = (
    "elements",
    "principles",
    "mechanisms",
    "categories",
    "indicators",
    "dimensions",
    "sources",
    "types",
    "domains",
    "functions",
    "steps",
    "components",
    "themes",
    "game changers",
    "forces",
    "levels",
    "features",
)
WHY_IT_MATTERS_KEYS = {
    "why this matters",
    "important implication",
    "important idea",
    "key insight",
    "key chapter takeaway",
    "key chapter implication",
    "central implication",
    "main integrated takeaway",
    "core kotter message",
}
EXAMPLE_KEYS = ("example", "examples")
RELATED_KEYS = (
    "compare",
    "comparison",
    "contrast",
    "distinction",
    "connection",
    "connections",
    "integration",
    "related",
    "linked",
    "vs",
)
LOW_VALUE_CARD_KEYS = {
    "chapter overview",
    "overview",
    "what can change",
    "why organizations matter",
    "technology and structure",
    "functions of culture",
    "motivations for global expansion",
    "challenges of international business",
    "netflix example",
    "chapter practice questions",
    "flashcards",
    "contrast with classical management",
    "key finding",
    "likely structural implications",
    "challenges of goal setting",
    "short-term effects",
    "long-term effects",
}
FRAMEWORK_ONLY_KEYS = {
    "five design variables",
    "the 3 c’s of collaboration",
    "the 3 c's of collaboration",
    "mintzberg’s five coordination mechanisms",
    "mintzberg's five coordination mechanisms",
    "miles and snow strategy typology",
    "porter’s competitive strategies",
    "porter's competitive strategies",
    "departmental technology categories",
    "stages of international evolution",
    "hofstede’s cultural dimensions theory",
    "hofstede's cultural dimensions theory",
    "four cultural indicators",
    "forces that shape managerial ethics",
    "factors influencing commitment",
    "future of work",
}
FRAMEWORK_COMPONENT_STOP_KEYS = {
    "benefit",
    "benefits",
    "downside",
    "downsides",
    "why it matters",
    "important note",
    "core logic",
    "implication",
    "implications",
    "common motivations",
    "what determines dependence",
    "likely structural implications",
}


@dataclass
class Node:
    title: str
    level: int
    lines: list[str] = field(default_factory=list)
    children: list["Node"] = field(default_factory=list)


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    chapters = []
    definitions = []
    cumulative_pool = []

    for order, chapter_meta in enumerate(manifest["chapters"], start=1):
        source_path = resolve_source_path(chapter_meta["file"])
        raw_text = read_source_text(source_path)
        root = parse_markdown_tree(raw_text)
        title, document_nodes = extract_document_nodes(root, chapter_meta["title"])

        overview_node = first_matching_node(document_nodes, is_overview_title)
        practice_node = first_matching_node(document_nodes, is_practice_title)

        content_nodes = [
            node
            for node in document_nodes
            if not is_overview_title(node.title)
            and not is_flashcard_title(node.title)
            and not is_practice_title(node.title)
            and "cumulative exam tags" not in normalize_key(node.title)
        ]

        chapter_definitions = collect_definitions(content_nodes, chapter_meta["id"], title)
        definitions.extend(chapter_definitions)

        flashcards = dedupe_flashcards(
            generate_definition_flashcards(chapter_definitions, chapter_meta["id"])
            + generate_concept_flashcards(content_nodes, chapter_meta["id"])
            + generate_framework_flashcards(content_nodes, chapter_meta["id"])
            + generate_comparison_flashcards(content_nodes, chapter_meta["id"])
            + generate_example_flashcards(content_nodes, chapter_meta["id"])
        )

        chapter_quiz = build_quiz_bank(title, chapter_meta["id"], flashcards, chapter_definitions)
        cumulative_pool.extend(chapter_quiz)

        chapter_payload = {
            "id": chapter_meta["id"],
            "order": order,
            "title": title,
            "nav_title": chapter_meta["title"],
            "topic_type": "guest" if "guest" in chapter_meta["id"] else "chapter",
            "overview_html": render_overview(overview_node),
            "content_html": render_content_nodes(content_nodes),
            "practice_questions": extract_practice_questions(practice_node),
            "flashcards": flashcards,
            "quiz": chapter_quiz,
            "definition_count": len(chapter_definitions),
            "flashcard_count": len(flashcards),
            "quiz_count": len(chapter_quiz),
        }
        chapters.append(chapter_payload)

    cumulative_sets = []
    running_quiz_pool = []
    for chapter in chapters:
        running_quiz_pool.extend(chapter["quiz"])
        cumulative_sets.append(
            {
                "chapter_id": chapter["id"],
                "title": chapter["title"],
                "questions": running_quiz_pool[:],
            }
        )

    site_payload = {
        "title": manifest["title"],
        "description": manifest["description"],
        "chapters": chapters,
        "definitions": definitions,
        "cumulative_quizzes": cumulative_sets,
        "final_exam": {
            "title": "Final Exam Mode",
            "questions": cumulative_pool,
        },
    }

    SITE_JSON_PATH.write_text(
        json.dumps(site_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {SITE_JSON_PATH}")


def read_source_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")
    if text.lstrip().startswith("{\\rtf1"):
        return convert_rtfish_text(text)
    return text


def resolve_source_path(relative_path: str) -> Path:
    direct = BUNDLE_DIR / relative_path
    if direct.exists():
        return direct

    chapters_dir = BUNDLE_DIR / "chapters"
    target_name = Path(relative_path).name
    if "guest_psychology_of_work" in target_name:
        alternate = chapters_dir / "guest_lecture_psychology_of_work.md"
        if alternate.exists():
            return alternate

    stem_key = normalize_key(Path(target_name).stem.replace("_", " "))
    for candidate in chapters_dir.glob("*.md"):
        candidate_key = normalize_key(candidate.stem.replace("_", " "))
        if candidate_key == stem_key or stem_key in candidate_key or candidate_key in stem_key:
            return candidate

    raise FileNotFoundError(f"Could not resolve chapter source for {relative_path}")


def convert_rtfish_text(text: str) -> str:
    def decode_hex(match: re.Match[str]) -> str:
        return bytes.fromhex(match.group(1)).decode("cp1252", errors="ignore")

    def decode_unicode(match: re.Match[str]) -> str:
        value = int(match.group(1))
        if value < 0:
            value += 65536
        try:
            return chr(value)
        except ValueError:
            return ""

    text = re.sub(r"\\'([0-9a-fA-F]{2})", decode_hex, text)
    text = re.sub(r"\\u(-?\d+)\??", decode_unicode, text)
    text = text.replace("\\\n", "\n")
    text = re.sub(r"\\[a-zA-Z]+\d* ?", "", text)
    text = text.replace("{", "").replace("}", "")

    cleaned_lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            cleaned_lines.append("")
            continue
        if line.startswith(("#", "-", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "---")):
            cleaned_lines.append(line)
            continue
        if re.match(r"^[A-Z][A-Za-z0-9& /()'\-:,.]+$", line):
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def parse_markdown_tree(text: str) -> Node:
    root = Node("root", 0)
    stack = [root]
    for line in text.splitlines():
        heading_match = HEADING_RE.match(line.strip())
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            node = Node(title=title, level=level)
            while stack and stack[-1].level >= level:
                stack.pop()
            stack[-1].children.append(node)
            stack.append(node)
        else:
            stack[-1].lines.append(line.rstrip())
    return root


def extract_document_nodes(root: Node, fallback_title: str) -> tuple[str, list[Node]]:
    if not root.children:
        return fallback_title, []
    first = root.children[0]
    if first.level == 1:
        title = first.title.strip() or fallback_title
        nodes = first.children + root.children[1:]
        return title, nodes
    return fallback_title, root.children


def normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def is_overview_title(title: str) -> bool:
    return normalize_key(title) in {"chapter overview", "overview"}


def is_flashcard_title(title: str) -> bool:
    key = normalize_key(title)
    return "flashcards" in key


def is_practice_title(title: str) -> bool:
    key = normalize_key(title)
    return "practice questions" in key


def first_matching_node(nodes: list[Node], predicate) -> Node | None:
    for node in nodes:
        if predicate(node.title):
            return node
    return None


def render_overview(node: Node | None) -> str:
    if not node:
        return ""
    return f'<section class="chapter-overview note-card">{render_node_body(node, 0)}</section>'


def render_content_nodes(nodes: list[Node]) -> str:
    parts = []
    for node in nodes:
        parts.append(render_content_node(node))
    return "".join(parts)


def render_content_node(node: Node) -> str:
    display = split_heading(node.title)
    if node.children and not meaningful_lines(node.lines) and display["badge"] and display["badge"].lower().startswith("part"):
        body = "".join(render_content_node(child) for child in node.children)
        return (
            '<section class="topic-group">'
            f'<div class="group-heading"><span class="group-badge">{html.escape(display["badge"])}</span>'
            f'<h2>{html.escape(display["title"])}</h2></div>'
            f"{body}</section>"
        )
    badge_html = f'<span class="concept-badge">{html.escape(display["badge"])}</span>' if display["badge"] else ""
    primary_blocks = render_primary_concept_blocks(node)
    supporting_blocks = "".join(render_supporting_block(child, 0) for child in node.children)
    return (
        '<section class="concept-card note-card">'
        f'<header class="concept-header">{badge_html}<h3>{html.escape(display["title"])}</h3></header>'
        f'<div class="concept-layout">{primary_blocks}{supporting_blocks}</div>'
        "</section>"
    )


def render_primary_concept_blocks(node: Node) -> str:
    title_key = normalize_key(node.title)
    definition_html = ""
    explanation_html = ""

    if title_key == "definition":
        paragraphs = [p for p in paragraph_text(node.lines) if p]
        if paragraphs:
            definition_html = f"<p>{render_inline(paragraphs[0])}</p>"
            if len(paragraphs) > 1:
                explanation_html = "".join(f"<p>{render_inline(paragraph)}</p>" for paragraph in paragraphs[1:])
    else:
        remaining_lines = []
        definition_parts = []
        for raw_line in node.lines:
            stripped = raw_line.strip()
            match = BOLD_DEFINITION_RE.match(stripped)
            if match:
                remainder = match.group(2).lstrip(": ").strip()
                if remainder:
                    definition_parts.append(f"<p>{render_inline(remainder)}</p>")
                continue
            remaining_lines.append(raw_line)
        definition_html = "".join(definition_parts)
        explanation_html = render_markdown_lines(remaining_lines)

    blocks = []
    if definition_html:
        blocks.append(render_detail_block("Definition", "", definition_html, "definition"))
    if explanation_html:
        explanation_title = "" if normalize_key(node.title) != "definition" else "Explanation"
        blocks.append(render_detail_block("Explanation", explanation_title, explanation_html, "explanation"))
    return "".join(blocks)


def render_supporting_block(node: Node, depth: int) -> str:
    label, title, tone = classify_detail_block(node)
    body_parts = []

    if meaningful_lines(node.lines):
        body_parts.append(render_markdown_lines(node.lines))

    for child in node.children:
        body_parts.append(render_supporting_block(child, depth + 1))

    content = "".join(part for part in body_parts if part)
    if not content:
        return ""
    return render_detail_block(label, title, content, tone, depth)


def classify_detail_block(node: Node) -> tuple[str, str, str]:
    display = split_heading(node.title)
    title = display["title"] or node.title
    key = normalize_key(title)
    list_items = extract_list_items(node.lines)

    if key in WHY_IT_MATTERS_KEYS:
        return ("Why it matters", "", "why")
    if any(token in key for token in EXAMPLE_KEYS):
        clean_title = title.replace("example", "").replace("Example", "").strip(" :-")
        return ("Example", clean_title, "example")
    if any(token in key for token in RELATED_KEYS):
        return ("Related concepts", title if key not in {"key distinction", "quick contrast"} else "", "related")
    if key in {"main elements of organizational design", "mechanisms", "forms", "common forms", "components"}:
        return ("Framework components", title if key != "components" else "", "framework")
    if len(list_items) >= 3 and any(keyword in key for keyword in FRAMEWORK_KEYWORDS):
        return ("Framework components", title, "framework")
    if key == "definition":
        return ("Definition", "", "definition")
    return ("Explanation", title if key not in GENERIC_TITLES else "", "explanation")


def render_detail_block(label: str, title: str, content: str, tone: str, depth: int = 0) -> str:
    title_html = f"<h4>{html.escape(title)}</h4>" if title else ""
    nested_class = " nested-detail" if depth else ""
    return (
        f'<section class="detail-block detail-{tone}{nested_class}">'
        f'<p class="detail-label">{html.escape(label)}</p>'
        f"{title_html}"
        f'<div class="detail-content">{content}</div>'
        "</section>"
    )


def render_node_body(node: Node, depth: int) -> str:
    parts = []
    block_html = render_markdown_lines(node.lines)
    if block_html:
        parts.append(block_html)
    for child in node.children:
        display = split_heading(child.title)
        tag = "h4" if depth == 0 else "h5"
        parts.append(
            '<section class="subtopic-block">'
            f"<{tag}>{html.escape(display['title'])}</{tag}>"
            f"{render_node_body(child, depth + 1)}"
            "</section>"
        )
    return "".join(parts)


def render_markdown_lines(lines: list[str]) -> str:
    output = []
    paragraph: list[str] = []
    list_type: str | None = None
    list_items: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(part.strip() for part in paragraph if part.strip())
            output.append(f"<p>{render_inline(text)}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items, list_type
        if list_items and list_type:
            tag = "ol" if list_type == "ol" else "ul"
            items = "".join(f"<li>{item}</li>" for item in list_items)
            output.append(f"<{tag}>{items}</{tag}>")
        list_items = []
        list_type = None

    for raw_line in lines + [""]:
        line = raw_line.strip()
        if not line or line == "---":
            flush_paragraph()
            flush_list()
            continue

        ordered_match = ORDERED_ITEM_RE.match(line)
        unordered_match = UNORDERED_ITEM_RE.match(line)

        if ordered_match:
            flush_paragraph()
            if list_type != "ol":
                flush_list()
                list_type = "ol"
            list_items.append(render_inline(ordered_match.group(2).strip()))
            continue

        if unordered_match:
            flush_paragraph()
            if list_type != "ul":
                flush_list()
                list_type = "ul"
            list_items.append(render_inline(unordered_match.group(1).strip()))
            continue

        flush_list()
        paragraph.append(line)

    return "".join(output)


def render_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", text)
    return text


def split_heading(title: str) -> dict[str, str | None]:
    clean = title.strip()
    part_match = re.match(r"^(Part [A-Z])\s+[—-]\s+(.+)$", clean)
    if part_match:
        return {"badge": part_match.group(1), "title": part_match.group(2)}
    number_match = re.match(r"^(\d+(?:\.\d+)*)\.\s*(.+)$", clean)
    if number_match:
        return {"badge": number_match.group(1), "title": number_match.group(2)}
    subnumber_match = re.match(r"^(\d+(?:\.\d+)*)\s+(.+)$", clean)
    if subnumber_match:
        return {"badge": subnumber_match.group(1), "title": subnumber_match.group(2)}
    return {"badge": None, "title": clean}


def meaningful_lines(lines: list[str]) -> bool:
    return any(line.strip() and line.strip() != "---" for line in lines)


def paragraph_text(lines: list[str]) -> list[str]:
    paragraphs = []
    current = []
    for raw_line in lines + [""]:
        line = raw_line.strip()
        if not line or line == "---":
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        if ORDERED_ITEM_RE.match(line) or UNORDERED_ITEM_RE.match(line):
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            paragraphs.append(re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line).strip())
            continue
        current.append(line)
    return paragraphs


def collect_definitions(nodes: list[Node], chapter_id: str, chapter_title: str) -> list[dict]:
    definitions: list[dict] = []

    def walk(node: Node, ancestors: list[str]) -> None:
        title = split_heading(node.title)["title"] or node.title
        term = resolve_term(title, ancestors)

        definition_text = extract_definition_from_node(node)
        if definition_text and term:
            definitions.append(
                {
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                    "term": term,
                    "definition": definition_text,
                }
            )

        for child in node.children:
            walk(child, ancestors + [title])

    for node in nodes:
        walk(node, [])

    seen = {}
    for entry in definitions:
        key = normalize_key(entry["term"])
        if key not in seen or len(entry["definition"]) > len(seen[key]["definition"]):
            seen[key] = entry
    return list(seen.values())


def extract_definition_from_node(node: Node) -> str | None:
    title_key = normalize_key(node.title)
    if title_key == "definition":
        paragraphs = [p for p in paragraph_text(node.lines) if p]
        if paragraphs:
            return clean_definition_text(paragraphs[0])

    for raw_line in node.lines:
        match = BOLD_DEFINITION_RE.match(raw_line.strip())
        if match:
            remainder = match.group(2).lstrip(": ").strip()
            if remainder:
                return clean_definition_text(remainder)
    return None


def clean_definition_text(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def resolve_term(title: str, ancestors: list[str]) -> str | None:
    key = normalize_key(title)
    if key not in GENERIC_TITLES:
        return title
    for ancestor in reversed(ancestors):
        if normalize_key(ancestor) not in GENERIC_TITLES:
            return ancestor
    return None


def extract_list_items(lines: list[str]) -> list[str]:
    items = []
    for line in lines:
        ordered = ORDERED_ITEM_RE.match(line.strip())
        unordered = UNORDERED_ITEM_RE.match(line.strip())
        if ordered:
            items.append(clean_definition_text(ordered.group(2)))
        elif unordered:
            items.append(clean_definition_text(unordered.group(1)))
    return items


def extract_ordered_list_items(lines: list[str]) -> list[str]:
    items = []
    for line in lines:
        ordered = ORDERED_ITEM_RE.match(line.strip())
        if ordered:
            items.append(clean_definition_text(ordered.group(2)))
    return items


def generate_definition_flashcards(definitions: list[dict], chapter_id: str) -> list[dict]:
    cards = []
    for entry in definitions:
        term = entry["term"]
        definition = entry["definition"]
        cards.append(make_flashcard(chapter_id, f"What is {term}?", definition, "definition", topic=term))
        if len(definition) <= 220 and not answer_leaks_in_prompt(term, definition):
            cards.append(
                make_flashcard(
                    chapter_id,
                    definition_recognition_prompt(definition),
                    term,
                    "recognition",
                    topic=term,
                )
            )
    return cards


def generate_concept_flashcards(nodes: list[Node], chapter_id: str) -> list[dict]:
    cards: list[dict] = []

    def walk(node: Node, ancestors: list[str]) -> None:
        title = split_heading(node.title)["title"] or node.title
        term = resolve_term(title, ancestors)
        if should_generate_concept_cards(node, term):
            summary = extract_concept_summary(node)
            if summary:
                cards.append(make_flashcard(chapter_id, f"What is {term}?", summary, "definition", topic=term))
                if len(summary) <= 220 and not answer_leaks_in_prompt(term, summary):
                    cards.append(
                        make_flashcard(
                            chapter_id,
                            definition_recognition_prompt(summary),
                            term,
                            "recognition",
                            topic=term,
                        )
                    )
        for child in node.children:
            walk(child, ancestors + [title])

    for node in nodes:
        walk(node, [])

    return cards


def generate_framework_flashcards(nodes: list[Node], chapter_id: str) -> list[dict]:
    cards: list[dict] = []

    def walk(node: Node, ancestors: list[str]) -> None:
        title = split_heading(node.title)["title"] or node.title
        items = extract_framework_components(node)
        key = normalize_key(title)
        if len(items) >= 3 and (any(keyword in key for keyword in FRAMEWORK_KEYWORDS) or key in FRAMEWORK_ONLY_KEYS):
            prompt = framework_prompt(title, items, ancestors)
            answer = "; ".join(items)
            cards.append(make_flashcard(chapter_id, prompt, answer, "framework", topic=title))
        for child in node.children:
            walk(child, ancestors + [title])

    for node in nodes:
        walk(node, [])
    return cards


def framework_prompt(title: str, items: list[str], ancestors: list[str]) -> str:
    lower_title = title.lower()
    parent = ancestors[-1] if ancestors else ""
    if lower_title.startswith(("what ", "which ")):
        return title
    if normalize_key(title) in GENERIC_TITLES and parent:
        return framework_prompt(parent, items, [])
    if lower_title == "four types":
        return "What are the four main types of interorganizational relationships?"
    if lower_title in {"four types", "three dimensions"} and parent:
        return f"What are the main components of {parent}?"
    if lower_title == "five game changers":
        return "What are the five game changers shaping the future of work?"
    if lower_title in {"main sources", "factors influencing commitment"} and parent:
        return f"What are the components of {parent}?"
    if lower_title == "rites and ceremonies types":
        return "What are the main types of rites and ceremonies?"
    if lower_title.startswith(("principles of ", "levels of ", "domains of ", "forces that shape ")):
        return f"What are the {lower_title}?"
    if any(token in lower_title for token in ("stage", "lifecycle", "evolution")):
        return f"What are the stages of {title}?"
    if any(token in lower_title for token in ("dimension", "indicator")):
        return f"What are the dimensions of {title}?"
    if any(token in lower_title for token in ("strategy", "typology", "types", "categories")):
        return f"What are the main components of {title}?"
    if any(token in lower_title for token in ("forces", "principles", "mechanisms", "variables", "sources", "domains", "game changers")):
        return f"What are the components of {title}?"
    if items and len(items) <= 6:
        return f"What are the main components of {title}?"
    return f"What are the components of {title}?"


def generate_comparison_flashcards(nodes: list[Node], chapter_id: str) -> list[dict]:
    cards: list[dict] = []

    def walk(node: Node) -> None:
        title = split_heading(node.title)["title"] or node.title
        if " vs. " in title.lower() or " vs " in title.lower():
            summary = summarize_node(node)
            if summary:
                cards.append(
                    make_flashcard(
                        chapter_id,
                        comparison_prompt(title),
                        summary,
                        "comparison",
                        topic=title,
                    )
                )
        for child in node.children:
            walk(child)

    for node in nodes:
        walk(node)

    cards.extend(generate_paired_comparison_flashcards(nodes, chapter_id))
    return cards


def generate_example_flashcards(nodes: list[Node], chapter_id: str) -> list[dict]:
    cards: list[dict] = []

    def walk(node: Node, ancestors: list[str]) -> None:
        title = split_heading(node.title)["title"] or node.title
        if "example" in normalize_key(title) and ancestors:
            paragraphs = [p for p in paragraph_text(node.lines) if p]
            prompt_text = paragraphs[0] if paragraphs else ""
            concept = split_heading(ancestors[-1])["title"] or ancestors[-1]
            if prompt_text and is_good_example_prompt(prompt_text, concept):
                cards.append(
                    make_flashcard(
                        chapter_id,
                        f"Which concept is illustrated by this scenario? {prompt_text}",
                        concept,
                        "example",
                        topic=concept,
                    )
                )
        for child in node.children:
            walk(child, ancestors + [title])

    for node in nodes:
        walk(node, [])
    return cards


def summarize_node(node: Node) -> str:
    pieces = []
    paragraphs = [line.strip() for line in node.lines if line.strip() and not ORDERED_ITEM_RE.match(line.strip()) and not UNORDERED_ITEM_RE.match(line.strip())]
    if paragraphs:
        pieces.append(" ".join(paragraphs))
    items = extract_list_items(node.lines)
    if items:
        pieces.append("; ".join(items))
    for child in node.children:
        child_items = extract_list_items(child.lines)
        if child_items:
            pieces.append(f"{split_heading(child.title)['title']}: {'; '.join(child_items)}")
    unique = []
    seen = set()
    for piece in pieces:
        key = normalize_key(piece)
        if piece and key not in seen:
            unique.append(piece)
            seen.add(key)
    return " ".join(unique).strip()


def definition_recognition_prompt(definition: str) -> str:
    text = clean_definition_text(definition).rstrip(".")
    if text:
        text = text[0].lower() + text[1:]
    return f"Which concept describes {text}?"


def comparison_prompt(title: str) -> str:
    clean_title = split_heading(title)["title"] or title
    return f"What is the key difference between {clean_title}?"


def extract_framework_components(node: Node) -> list[str]:
    ordered_items = [
        normalize_component_label(item)
        for item in extract_ordered_list_items(node.lines)
        if normalize_key(normalize_component_label(item)) not in FRAMEWORK_COMPONENT_STOP_KEYS
    ]
    source_items = ordered_items if len(ordered_items) >= 3 else extract_list_items(node.lines)
    items = [
        normalize_component_label(item)
        for item in source_items
        if normalize_key(normalize_component_label(item)) not in FRAMEWORK_COMPONENT_STOP_KEYS
    ]
    child_titles: list[str] = []
    if len(items) < 3:
        child_titles = [
            normalize_component_label(split_heading(child.title)["title"] or child.title)
            for child in node.children
            if normalize_key(split_heading(child.title)["title"] or child.title) not in GENERIC_TITLES
            and normalize_key(split_heading(child.title)["title"] or child.title) not in WHY_IT_MATTERS_KEYS
            and normalize_key(split_heading(child.title)["title"] or child.title) not in FRAMEWORK_COMPONENT_STOP_KEYS
        ]

    combined: list[str] = []
    seen = set()
    for item in items + child_titles:
        key = normalize_key(item)
        if item and key not in seen and len(item.split()) <= 10:
            combined.append(item)
            seen.add(key)
    return combined


def normalize_component_label(text: str) -> str:
    cleaned = clean_definition_text(text)
    bold = re.search(r"\*\*(.+?)\*\*", text)
    if bold:
        return clean_definition_text(bold.group(1))
    bold_match = re.match(r"^([^:—-]{1,80}?)(?:\s*[—:-]\s+.+)?$", cleaned)
    if bold_match:
        cleaned = bold_match.group(1).strip()
    return cleaned


def should_generate_concept_cards(node: Node, term: str | None) -> bool:
    if not term:
        return False
    node_key = normalize_key(split_heading(node.title)["title"] or node.title)
    key = normalize_key(term)
    if node_key in GENERIC_TITLES or node_key in WHY_IT_MATTERS_KEYS:
        return False
    if key in GENERIC_TITLES or key in LOW_VALUE_CARD_KEYS or key in FRAMEWORK_ONLY_KEYS:
        return False
    if any(keyword in key for keyword in FRAMEWORK_KEYWORDS):
        return False
    if len(extract_framework_components(node)) >= 3:
        return False
    if " vs " in key or " vs. " in key:
        return False
    if term.endswith("?") or key.startswith(("why ", "how ", "what ")):
        return False
    if any(token in key for token in ("example", "questions", "flashcards")):
        return False
    return bool(extract_concept_summary(node))


def extract_concept_summary(node: Node) -> str | None:
    definition = extract_definition_from_node(node)
    if definition:
        return definition

    paragraphs = [
        p
        for p in paragraph_text(node.lines)
        if p and not p.lower().startswith(("examples:", "related concepts"))
    ]
    if paragraphs:
        summary = " ".join(paragraphs[:2]).strip()
        if 6 <= len(summary.split()) <= 60:
            return clean_definition_text(summary)

    if len(node.children) == 1 and normalize_key(node.children[0].title) == "definition":
        child_definition = extract_definition_from_node(node.children[0])
        if child_definition:
            return child_definition
    return None


def answer_leaks_in_prompt(term: str, prompt_body: str) -> bool:
    term_key = normalize_key(term).replace("’", "'")
    prompt_key = normalize_key(prompt_body).replace("’", "'")
    if not term_key:
        return False
    return term_key in prompt_key


def is_good_example_prompt(text: str, concept: str) -> bool:
    cleaned = clean_definition_text(text)
    if len(cleaned.split()) < 8 or len(cleaned.split()) > 34:
        return False
    if answer_leaks_in_prompt(concept, cleaned):
        return False
    banned = ("this class", "this answer", "used to illustrate", "example captures this logic")
    return not any(token in normalize_key(cleaned) for token in banned)


def generate_paired_comparison_flashcards(nodes: list[Node], chapter_id: str) -> list[dict]:
    cards: list[dict] = []
    indexed = index_nodes_by_title(nodes)
    comparison_pairs = [
        ("Mission", "Vision"),
        ("Classical Management", "Contemporary Management"),
        ("Effectiveness", "Efficiency"),
        ("Official Goals", "Operative Goals"),
        ("Vertical Information Linkages", "Horizontal Information Linkages"),
        ("Upward Communication", "Upward Voice"),
        ("Core technology", "Noncore technology"),
        ("Incremental Change", "Radical Change"),
        ("Positional Power", "Personal Power"),
    ]

    for left, right in comparison_pairs:
        left_node = indexed.get(normalize_key(left))
        right_node = indexed.get(normalize_key(right))
        if not left_node or not right_node:
            continue
        left_summary = extract_concept_summary(left_node)
        right_summary = extract_concept_summary(right_node)
        if not left_summary or not right_summary:
            continue
        left_clause = strip_term_prefix(left, left_summary)
        right_clause = strip_term_prefix(right, right_summary)
        answer = f"{left} {left_clause}, while {right} {right_clause}"
        cards.append(
            make_flashcard(
                chapter_id,
                f"What is the key difference between {left} and {right}?",
                answer.rstrip(".") + ".",
                "comparison",
                topic=f"{left} vs {right}",
            )
        )
    return cards


def index_nodes_by_title(nodes: list[Node]) -> dict[str, Node]:
    indexed: dict[str, Node] = {}

    def walk(node: Node) -> None:
        title = split_heading(node.title)["title"] or node.title
        key = normalize_key(title)
        indexed.setdefault(key, node)
        for child in node.children:
            walk(child)

    for node in nodes:
        walk(node)
    return indexed


def strip_term_prefix(term: str, summary: str) -> str:
    cleaned = clean_definition_text(summary).rstrip(".")
    pattern = re.compile(rf"^{re.escape(term)}\s+(is|are)\s+", re.IGNORECASE)
    if pattern.match(cleaned):
        return pattern.sub(lambda match: match.group(1) + " ", cleaned).strip()
    if cleaned:
        return cleaned[0].lower() + cleaned[1:]
    return cleaned


def extract_practice_questions(node: Node | None) -> list[dict]:
    if not node:
        return []
    questions: list[dict] = []

    def walk(current: Node, category: str | None = None) -> None:
        next_category = category
        title_key = normalize_key(current.title)
        if not is_practice_title(current.title) and title_key not in {"conceptual questions", "applied questions"}:
            next_category = split_heading(current.title)["title"] or current.title
        elif title_key in {"conceptual questions", "applied questions"}:
            next_category = split_heading(current.title)["title"] or current.title

        for line in current.lines:
            ordered = ORDERED_ITEM_RE.match(line.strip())
            if ordered:
                questions.append(
                    {
                        "prompt": clean_definition_text(ordered.group(2)),
                        "category": next_category or "Practice",
                    }
                )
        for child in current.children:
            walk(child, next_category)

    walk(node)
    return questions


def build_quiz_bank(chapter_title: str, chapter_id: str, flashcards: list[dict], definitions: list[dict]) -> list[dict]:
    questions: list[dict] = []
    definition_pairs = []

    for entry in definitions:
        definition_pairs.append((entry["term"], entry["definition"]))

    for card in flashcards:
        term = infer_term(card["front"])
        if term and looks_definition_like(card["back"]):
            definition_pairs.append((term, card["back"]))

    definition_pairs = dedupe_definition_pairs(definition_pairs)

    for index, (term, definition) in enumerate(definition_pairs):
        distractor_defs = pick_distractors(definition, [pair[1] for pair in definition_pairs if pair[0] != term], 3)
        if len(distractor_defs) == 3:
            questions.append(
                {
                    "id": f"{chapter_id}-term-{index}",
                    "type": "multiple_choice",
                    "prompt": f"Which definition best matches {term}?",
                    "options": shuffle_like([definition] + distractor_defs),
                    "answer": definition,
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                }
            )

        distractor_terms = pick_distractors(term, [pair[0] for pair in definition_pairs if pair[0] != term], 3)
        if len(distractor_terms) == 3:
            questions.append(
                {
                    "id": f"{chapter_id}-def-{index}",
                    "type": "multiple_choice",
                    "prompt": f"Which concept matches this description? {definition}",
                    "options": shuffle_like([term] + distractor_terms),
                    "answer": term,
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                }
            )

    for index, card in enumerate(flashcards):
        if len(card["back"]) > 260:
            continue
        distractor_backs = pick_distractors(
            card["back"],
            [other["back"] for other in flashcards if other["id"] != card["id"] and len(other["back"]) <= 260],
            3,
        )
        if len(distractor_backs) == 3:
            questions.append(
                {
                    "id": f"{chapter_id}-card-{index}",
                    "type": "multiple_choice",
                    "prompt": card["front"],
                    "options": shuffle_like([card["back"]] + distractor_backs),
                    "answer": card["back"],
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                }
            )

    for index, card in enumerate(flashcards):
        list_items = split_semicolon_list(card["back"])
        if card["kind"] == "framework" and 3 <= len(list_items) <= 12:
            correct = list_items[0]
            other_components = []
            for other in flashcards:
                if other["id"] == card["id"]:
                    continue
                other_components.extend(split_semicolon_list(other["back"]))
            distractors = pick_distractors(correct, other_components, 3)
            if len(distractors) == 3:
                questions.append(
                    {
                        "id": f"{chapter_id}-framework-{index}",
                        "type": "multiple_choice",
                        "prompt": f"Which of the following belongs in this set: {card['front']}",
                        "options": shuffle_like([correct] + distractors),
                        "answer": correct,
                        "chapter_id": chapter_id,
                        "chapter_title": chapter_title,
                    }
                )

    seen = {}
    for question in questions:
        key = normalize_key(question["prompt"])
        if key not in seen:
            seen[key] = question
    return list(seen.values())


def infer_term(front: str) -> str | None:
    front = front.strip().rstrip("?")
    patterns = [
        r"^What is (.+)$",
        r"^What are (.+)$",
        r"^Define (.+)$",
        r"^Which concept matches this definition: .+$",
    ]
    for pattern in patterns:
        match = re.match(pattern, front, re.IGNORECASE)
        if match and match.lastindex:
            return split_heading(match.group(1).strip())["title"]
    if len(front.split()) <= 6 and not front.endswith("."):
        return split_heading(front)["title"]
    return None


def looks_definition_like(text: str) -> bool:
    return len(text.split()) >= 5 and not text.endswith("?")


def dedupe_definition_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    best = {}
    for term, definition in pairs:
        key = normalize_key(term)
        if key not in best or len(definition) > len(best[key][1]):
            best[key] = (term, definition)
    return list(best.values())


def split_semicolon_list(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r";|, and |, ", text) if part.strip()]
    return [part for part in parts if len(part.split()) <= 12]


def pick_distractors(correct: str, pool: list[str], count: int) -> list[str]:
    choices = []
    seen = {normalize_key(correct)}
    for item in pool:
        key = normalize_key(item)
        if key in seen or not item.strip():
            continue
        choices.append(item)
        seen.add(key)
        if len(choices) == count:
            break
    return choices


def shuffle_like(options: list[str]) -> list[str]:
    return sorted(options, key=lambda item: normalize_key(item))


def make_flashcard(chapter_id: str, front: str, back: str, kind: str, topic: str | None = None) -> dict:
    return {
        "id": flashcard_id(chapter_id, front, back),
        "chapter_id": chapter_id,
        "front": clean_flashcard_front(front, kind),
        "back": clean_definition_text(back),
        "kind": kind,
        "topic": topic or infer_term(front) or front,
    }


def flashcard_id(chapter_id: str, front: str, back: str) -> str:
    token = normalize_key(f"{front}::{back}")
    token = re.sub(r"[^a-z0-9]+", "-", token).strip("-")
    return f"{chapter_id}-{token[:64]}"


def dedupe_flashcards(cards: list[dict]) -> list[dict]:
    exact = {}
    for card in cards:
        if not is_flashcard_high_quality(card):
            continue
        exact_key = normalize_key(f"{card['front']}::{card['back']}")
        current = exact.get(exact_key)
        if not current or score_flashcard(card) > score_flashcard(current):
            exact[exact_key] = card

    limited = {}
    for card in exact.values():
        topic = normalize_key(card.get("topic") or infer_term(card["front"]) or card["front"])
        kind_bucket = flashcard_kind_bucket(card["kind"])
        key = f"{topic}::{kind_bucket}"
        current = limited.get(key)
        if not current or score_flashcard(card) > score_flashcard(current):
            limited[key] = card

    unique_fronts = {}
    for card in limited.values():
        front_key = normalize_key(card["front"])
        current = unique_fronts.get(front_key)
        if not current or score_flashcard(card) > score_flashcard(current):
            unique_fronts[front_key] = card

    return sorted(unique_fronts.values(), key=lambda card: (card["chapter_id"], normalize_key(card["front"])))


def score_flashcard(card: dict) -> tuple[int, int, int]:
    kind_priority = {
        "framework": 5,
        "comparison": 4,
        "definition": 3,
        "recognition": 2,
        "example": 1,
    }
    return (
        kind_priority.get(card["kind"], 0),
        min(len(card["back"]), 260),
        -len(card["front"]),
    )


def clean_flashcard_front(front: str, kind: str) -> str:
    cleaned = clean_definition_text(front).rstrip(".")
    if kind == "comparison" and not cleaned.endswith("?"):
        cleaned = cleaned + "?"
    if kind == "example" and not cleaned.startswith("Which concept is illustrated by this scenario?"):
        cleaned = f"Which concept is illustrated by this scenario? {cleaned}"
    if kind in {"definition", "recognition", "framework"} and not cleaned.endswith("?"):
        cleaned = cleaned + "?"
    return cleaned


def flashcard_kind_bucket(kind: str) -> str:
    if kind in {"definition", "recognition", "example"}:
        return kind
    return f"{kind}:{kind}"


def is_flashcard_high_quality(card: dict) -> bool:
    front = card["front"].strip()
    back = card["back"].strip()
    topic = card.get("topic") or ""

    if not front or not back:
        return False
    if len(front.split()) > 38 or len(back.split()) > 80:
        return False
    if normalize_key(front) in LOW_VALUE_CARD_KEYS:
        return False
    if any(token in normalize_key(front) for token in ("this class", "this answer is more complicated", "used to illustrate what concept")):
        return False
    if card["kind"] in {"recognition", "example"} and answer_leaks_in_prompt(topic, front):
        return False
    if card["kind"] == "example" and not is_good_example_prompt(front.replace("Which concept is illustrated by this scenario?", "").strip(), topic):
        return False
    return True


if __name__ == "__main__":
    main()

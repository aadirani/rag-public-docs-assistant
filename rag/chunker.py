"""Split Markdown documents into small, titled chunks that can be retrieved on their own."""

import re

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def _split_long(body, max_words):
    """Break a long section at paragraph boundaries into pieces of about max_words."""
    pieces, current, count = [], [], 0
    for para in re.split(r"\n\s*\n", body):
        words = len(para.split())
        if current and count + words > max_words:
            pieces.append("\n\n".join(current))
            current, count = [], 0
        current.append(para)
        count += words
    if current:
        pieces.append("\n\n".join(current))
    return pieces


def split_markdown(text, source, max_words=180):
    """Return chunks: {id, source, heading, text}. The heading is the full path, e.g. 'A > B'.

    Diagram code blocks (```mermaid) are skipped: they're drawing instructions, not prose.
    """
    chunks, path, buf = [], [], []
    in_fence, skip_fence = False, False

    def flush():
        body = "\n".join(buf).strip()
        buf.clear()
        if not body:
            return
        heading = " > ".join(path) or source
        for part in _split_long(body, max_words):
            chunks.append({"id": f"{source}#{len(chunks)}", "source": source,
                           "heading": heading, "text": part})

    for line in text.splitlines():
        if line.startswith("```"):
            if not in_fence:
                in_fence, skip_fence = True, line.strip().startswith("```mermaid")
                if skip_fence:
                    continue
            else:
                in_fence = False
                if skip_fence:
                    skip_fence = False
                    continue
        if skip_fence:
            continue
        match = None if in_fence else HEADING.match(line)
        if match:
            flush()
            level = len(match.group(1))
            path[:] = path[:level - 1] + [match.group(2).strip()]
        else:
            buf.append(line)
    flush()
    return chunks

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class HtmlNode:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    parent: HtmlNode | None = None
    children: list["HtmlNode"] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)

    def add_child(self, child: "HtmlNode") -> None:
        self.children.append(child)

    def descendants(self) -> list["HtmlNode"]:
        nodes: list[HtmlNode] = []
        for child in self.children:
            nodes.append(child)
            nodes.extend(child.descendants())
        return nodes

    def text_content(self) -> str:
        parts = list(self.text_parts)
        for child in self.children:
            child_text = child.text_content()
            if child_text:
                parts.append(child_text)
        return " ".join(part.strip() for part in parts if part and part.strip()).strip()


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = HtmlNode(tag="document")
        self.stack = [self.root]
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower_tag = tag.lower()
        if lower_tag in {"script", "style"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        node = HtmlNode(
            tag=lower_tag,
            attrs={key.lower(): (value or "") for key, value in attrs},
            parent=self.stack[-1],
        )
        self.stack[-1].add_child(node)
        self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        lower_tag = tag.lower()
        if lower_tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if len(self.stack) > 1:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.stack[-1].text_parts.append(data)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def parse_html_document(html: str) -> HtmlNode:
    parser = _TreeBuilder()
    parser.feed(html)
    parser.close()
    return parser.root


def select_all(root: HtmlNode, selector: str) -> list[HtmlNode]:
    current = [root]
    for token in [part.strip() for part in selector.split() if part.strip()]:
        next_nodes: list[HtmlNode] = []
        for node in current:
            for descendant in node.descendants():
                if _matches(descendant, token):
                    next_nodes.append(descendant)
        current = _dedupe_nodes(next_nodes)
    return current


def select_first(root: HtmlNode, selector: str) -> HtmlNode | None:
    matches = select_all(root, selector)
    return matches[0] if matches else None


def _dedupe_nodes(nodes: list[HtmlNode]) -> list[HtmlNode]:
    seen: set[int] = set()
    unique: list[HtmlNode] = []
    for node in nodes:
        identity = id(node)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(node)
    return unique


def _matches(node: HtmlNode, token: str) -> bool:
    tag_name, identifier, classes = _parse_token(token)
    if tag_name and node.tag != tag_name:
        return False
    if identifier and node.attrs.get("id", "").lower() != identifier:
        return False
    node_classes = {value.strip().lower() for value in node.attrs.get("class", "").split() if value.strip()}
    return all(class_name in node_classes for class_name in classes)


def _parse_token(token: str) -> tuple[str | None, str | None, list[str]]:
    tag_name: str | None = None
    identifier: str | None = None
    classes: list[str] = []
    remainder = token.strip()

    if "#" in remainder:
        before_id, after_id = remainder.split("#", 1)
        remainder = before_id
        if "." in after_id:
            identifier, trailing = after_id.split(".", 1)
            classes.extend(part.lower() for part in trailing.split(".") if part)
        else:
            identifier = after_id

    if "." in remainder:
        before_class, *class_parts = remainder.split(".")
        remainder = before_class
        classes.extend(part.lower() for part in class_parts if part)

    if remainder:
        tag_name = remainder.lower()

    return tag_name, identifier.lower() if identifier else None, classes

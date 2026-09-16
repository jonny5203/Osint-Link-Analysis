"""Namespace-agnostic helpers for reading large sanctions XML files.

Every publisher here has changed its XML namespace at least once, so all
matching in this package is on local names ("sdnEntry"), never on the full
tag name that carries the namespace URI. The EU and UN parsers under
sources/eu and sources/un read their files through the same helpers.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from lxml import etree


def local_name(tag: object) -> str:
    """Return "sdnEntry" for "{http://some-namespace}sdnEntry".

    Comments and processing instructions have no string tag, so they return ""
    and can never accidentally match an element name.
    """
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def child_elements(elem: etree._Element, name: str) -> list[etree._Element]:
    """Direct children of elem whose local name is name, in document order."""
    return [child for child in elem if local_name(child.tag) == name]


def first_child(elem: etree._Element, name: str) -> etree._Element | None:
    for child in child_elements(elem, name):
        return child
    return None


def child_text(elem: etree._Element, name: str) -> str | None:
    """Text of the first matching child, trimmed.

    Returns None when the child is missing or holds nothing but whitespace, so
    callers can treat absent and blank the same way the record hash does.
    """
    child = first_child(elem, name)
    if child is None or child.text is None:
        return None
    text = child.text.strip()
    return text or None


def stream_entries(xml_path: Path, entry_local_name: str) -> Iterator[etree._Element]:
    """Yield finished entry elements from an XML file, one at a time.

    lxml's iterparse reports each element when its closing tag has been read, so
    the file is never loaded as one tree. After the consumer is done with one
    entry, two cleanup steps keep memory flat on a file that spans hundreds of
    megabytes. elem.clear() empties the entry. Deleting the siblings before the
    entry detaches the emptied husks from the parent. Without the second step
    the parent keeps every cleared child in its child list, and memory still
    grows with the length of the file.
    """
    for _event, elem in etree.iterparse(str(xml_path), events=("end",)):
        if local_name(elem.tag) != entry_local_name:
            continue
        yield elem
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="DocEntry")


@_attrs_define
class DocEntry:
    """Index entry for a documentation page.

    Attributes:
        slug (str): URL-safe identifier, used as the path segment.
        title (str):
        section (str): Top-level grouping for the docs sidebar.
        available (bool): True iff the markdown file exists on disk.
    """

    slug: str
    title: str
    section: str
    available: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        slug = self.slug

        title = self.title

        section = self.section

        available = self.available

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "slug": slug,
                "title": title,
                "section": section,
                "available": available,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        slug = d.pop("slug")

        title = d.pop("title")

        section = d.pop("section")

        available = d.pop("available")

        doc_entry = cls(
            slug=slug,
            title=title,
            section=section,
            available=available,
        )

        doc_entry.additional_properties = d
        return doc_entry

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties

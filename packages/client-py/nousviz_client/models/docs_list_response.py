from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.doc_entry import DocEntry


T = TypeVar("T", bound="DocsListResponse")


@_attrs_define
class DocsListResponse:
    """GET /api/docs — index of all documentation pages.

    Attributes:
        docs (list[DocEntry]):
    """

    docs: list[DocEntry]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        docs = []
        for docs_item_data in self.docs:
            docs_item = docs_item_data.to_dict()
            docs.append(docs_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "docs": docs,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.doc_entry import DocEntry

        d = dict(src_dict)
        docs = []
        _docs = d.pop("docs")
        for docs_item_data in _docs:
            docs_item = DocEntry.from_dict(docs_item_data)

            docs.append(docs_item)

        docs_list_response = cls(
            docs=docs,
        )

        docs_list_response.additional_properties = d
        return docs_list_response

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

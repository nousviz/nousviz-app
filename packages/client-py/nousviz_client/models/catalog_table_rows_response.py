from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.catalog_table_rows_response_rows_item import CatalogTableRowsResponseRowsItem


T = TypeVar("T", bound="CatalogTableRowsResponse")


@_attrs_define
class CatalogTableRowsResponse:
    """GET /api/catalog/plugins/{plugin_id}/tables/{table_name}/rows.

    Attributes:
        rows (list[CatalogTableRowsResponseRowsItem]):
        total (int):
        page (int):
        limit (int):
    """

    rows: list[CatalogTableRowsResponseRowsItem]
    total: int
    page: int
    limit: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        rows = []
        for rows_item_data in self.rows:
            rows_item = rows_item_data.to_dict()
            rows.append(rows_item)

        total = self.total

        page = self.page

        limit = self.limit

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "rows": rows,
                "total": total,
                "page": page,
                "limit": limit,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.catalog_table_rows_response_rows_item import CatalogTableRowsResponseRowsItem

        d = dict(src_dict)
        rows = []
        _rows = d.pop("rows")
        for rows_item_data in _rows:
            rows_item = CatalogTableRowsResponseRowsItem.from_dict(rows_item_data)

            rows.append(rows_item)

        total = d.pop("total")

        page = d.pop("page")

        limit = d.pop("limit")

        catalog_table_rows_response = cls(
            rows=rows,
            total=total,
            page=page,
            limit=limit,
        )

        catalog_table_rows_response.additional_properties = d
        return catalog_table_rows_response

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

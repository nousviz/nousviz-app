from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.dataport_tab_rows_response_rows_item import DataportTabRowsResponseRowsItem


T = TypeVar("T", bound="DataportTabRowsResponse")


@_attrs_define
class DataportTabRowsResponse:
    """GET /api/data-port/plugins/{plugin_slug}/tab/{tab_id}.

    Paginated rows from the tab's declared SQL table. `rows` is a list
    of plugin-table-shaped dicts (column types vary per table), so
    typed as `list[dict[str, Any]]` rather than a fixed shape.

        Attributes:
            rows (list[DataportTabRowsResponseRowsItem]):
            total (int):
            page (int):
            page_size (int):
    """

    rows: list[DataportTabRowsResponseRowsItem]
    total: int
    page: int
    page_size: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        rows = []
        for rows_item_data in self.rows:
            rows_item = rows_item_data.to_dict()
            rows.append(rows_item)

        total = self.total

        page = self.page

        page_size = self.page_size

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "rows": rows,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dataport_tab_rows_response_rows_item import DataportTabRowsResponseRowsItem

        d = dict(src_dict)
        rows = []
        _rows = d.pop("rows")
        for rows_item_data in _rows:
            rows_item = DataportTabRowsResponseRowsItem.from_dict(rows_item_data)

            rows.append(rows_item)

        total = d.pop("total")

        page = d.pop("page")

        page_size = d.pop("page_size")

        dataport_tab_rows_response = cls(
            rows=rows,
            total=total,
            page=page,
            page_size=page_size,
        )

        dataport_tab_rows_response.additional_properties = d
        return dataport_tab_rows_response

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

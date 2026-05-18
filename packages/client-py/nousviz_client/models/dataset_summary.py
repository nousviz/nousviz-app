from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.dataset_summary_column_types import DatasetSummaryColumnTypes


T = TypeVar("T", bound="DatasetSummary")


@_attrs_define
class DatasetSummary:
    """A single datasets row in the list response — metadata only, no `data` blob.

    Attributes:
        id (str):
        name (str):
        slug (str):
        description (None | str | Unset):
        columns (list[str] | Unset): Column names in the order they appeared in the source CSV.
        column_types (DatasetSummaryColumnTypes | Unset): Inferred type per column ('number' | 'string' | etc.) — used
            for sort + render hints.
        row_count (int | Unset):  Default: 0.
        file_size (int | None | Unset): Total stored size in bytes.
        tags (list[str] | Unset): Operator-assigned labels.
        uploaded_at (None | str | Unset):
        updated_at (None | str | Unset):
    """

    id: str
    name: str
    slug: str
    description: None | str | Unset = UNSET
    columns: list[str] | Unset = UNSET
    column_types: DatasetSummaryColumnTypes | Unset = UNSET
    row_count: int | Unset = 0
    file_size: int | None | Unset = UNSET
    tags: list[str] | Unset = UNSET
    uploaded_at: None | str | Unset = UNSET
    updated_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        slug = self.slug

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        columns: list[str] | Unset = UNSET
        if not isinstance(self.columns, Unset):
            columns = self.columns

        column_types: dict[str, Any] | Unset = UNSET
        if not isinstance(self.column_types, Unset):
            column_types = self.column_types.to_dict()

        row_count = self.row_count

        file_size: int | None | Unset
        if isinstance(self.file_size, Unset):
            file_size = UNSET
        else:
            file_size = self.file_size

        tags: list[str] | Unset = UNSET
        if not isinstance(self.tags, Unset):
            tags = self.tags

        uploaded_at: None | str | Unset
        if isinstance(self.uploaded_at, Unset):
            uploaded_at = UNSET
        else:
            uploaded_at = self.uploaded_at

        updated_at: None | str | Unset
        if isinstance(self.updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = self.updated_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "slug": slug,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if columns is not UNSET:
            field_dict["columns"] = columns
        if column_types is not UNSET:
            field_dict["column_types"] = column_types
        if row_count is not UNSET:
            field_dict["row_count"] = row_count
        if file_size is not UNSET:
            field_dict["file_size"] = file_size
        if tags is not UNSET:
            field_dict["tags"] = tags
        if uploaded_at is not UNSET:
            field_dict["uploaded_at"] = uploaded_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dataset_summary_column_types import DatasetSummaryColumnTypes

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        slug = d.pop("slug")

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        columns = cast(list[str], d.pop("columns", UNSET))

        _column_types = d.pop("column_types", UNSET)
        column_types: DatasetSummaryColumnTypes | Unset
        if isinstance(_column_types, Unset):
            column_types = UNSET
        else:
            column_types = DatasetSummaryColumnTypes.from_dict(_column_types)

        row_count = d.pop("row_count", UNSET)

        def _parse_file_size(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        file_size = _parse_file_size(d.pop("file_size", UNSET))

        tags = cast(list[str], d.pop("tags", UNSET))

        def _parse_uploaded_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        uploaded_at = _parse_uploaded_at(d.pop("uploaded_at", UNSET))

        def _parse_updated_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        updated_at = _parse_updated_at(d.pop("updated_at", UNSET))

        dataset_summary = cls(
            id=id,
            name=name,
            slug=slug,
            description=description,
            columns=columns,
            column_types=column_types,
            row_count=row_count,
            file_size=file_size,
            tags=tags,
            uploaded_at=uploaded_at,
            updated_at=updated_at,
        )

        dataset_summary.additional_properties = d
        return dataset_summary

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

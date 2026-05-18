from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.dataset_detail_response_column_types import DatasetDetailResponseColumnTypes


T = TypeVar("T", bound="DatasetDetailResponse")


@_attrs_define
class DatasetDetailResponse:
    """GET /api/datasets/{slug} — full dataset including the `data` blob.

    Sort + paginate happens server-side; `total_rows` is the unpaginated
    count, `data` carries the (possibly sliced) row matrix.

        Attributes:
            id (str):
            name (str):
            slug (str):
            columns (list[str]):
            column_types (DatasetDetailResponseColumnTypes):
            data (list[list[Any]]): Row-major matrix; inner list values match `columns` ordering.
            row_count (int):
            total_rows (int):
            description (None | str | Unset):
            file_size (int | None | Unset):
            tags (list[str] | Unset): Operator-assigned labels.
            uploaded_at (None | str | Unset):
            updated_at (None | str | Unset):
            data_as_of (None | str | Unset):
    """

    id: str
    name: str
    slug: str
    columns: list[str]
    column_types: DatasetDetailResponseColumnTypes
    data: list[list[Any]]
    row_count: int
    total_rows: int
    description: None | str | Unset = UNSET
    file_size: int | None | Unset = UNSET
    tags: list[str] | Unset = UNSET
    uploaded_at: None | str | Unset = UNSET
    updated_at: None | str | Unset = UNSET
    data_as_of: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        slug = self.slug

        columns = self.columns

        column_types = self.column_types.to_dict()

        data = []
        for data_item_data in self.data:
            data_item = data_item_data

            data.append(data_item)

        row_count = self.row_count

        total_rows = self.total_rows

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

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

        data_as_of: None | str | Unset
        if isinstance(self.data_as_of, Unset):
            data_as_of = UNSET
        else:
            data_as_of = self.data_as_of

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "slug": slug,
                "columns": columns,
                "column_types": column_types,
                "data": data,
                "row_count": row_count,
                "total_rows": total_rows,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if file_size is not UNSET:
            field_dict["file_size"] = file_size
        if tags is not UNSET:
            field_dict["tags"] = tags
        if uploaded_at is not UNSET:
            field_dict["uploaded_at"] = uploaded_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at
        if data_as_of is not UNSET:
            field_dict["data_as_of"] = data_as_of

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dataset_detail_response_column_types import DatasetDetailResponseColumnTypes

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        slug = d.pop("slug")

        columns = cast(list[str], d.pop("columns"))

        column_types = DatasetDetailResponseColumnTypes.from_dict(d.pop("column_types"))

        data = []
        _data = d.pop("data")
        for data_item_data in _data:
            data_item = cast(list[Any], data_item_data)

            data.append(data_item)

        row_count = d.pop("row_count")

        total_rows = d.pop("total_rows")

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

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

        def _parse_data_as_of(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        data_as_of = _parse_data_as_of(d.pop("data_as_of", UNSET))

        dataset_detail_response = cls(
            id=id,
            name=name,
            slug=slug,
            columns=columns,
            column_types=column_types,
            data=data,
            row_count=row_count,
            total_rows=total_rows,
            description=description,
            file_size=file_size,
            tags=tags,
            uploaded_at=uploaded_at,
            updated_at=updated_at,
            data_as_of=data_as_of,
        )

        dataset_detail_response.additional_properties = d
        return dataset_detail_response

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

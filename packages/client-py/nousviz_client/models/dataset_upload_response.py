from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.dataset_upload_response_column_types import DatasetUploadResponseColumnTypes


T = TypeVar("T", bound="DatasetUploadResponse")


@_attrs_define
class DatasetUploadResponse:
    """POST /api/datasets/upload — newly stored dataset row.

    Same shape as DatasetSummary plus the `id` returned by the
    upsert.

        Attributes:
            id (str):
            name (str):
            slug (str):
            row_count (int):
            file_size (int):
            columns (list[str]):
            column_types (DatasetUploadResponseColumnTypes):
            uploaded_at (None | str | Unset):
            updated_at (None | str | Unset):
    """

    id: str
    name: str
    slug: str
    row_count: int
    file_size: int
    columns: list[str]
    column_types: DatasetUploadResponseColumnTypes
    uploaded_at: None | str | Unset = UNSET
    updated_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        slug = self.slug

        row_count = self.row_count

        file_size = self.file_size

        columns = self.columns

        column_types = self.column_types.to_dict()

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
                "row_count": row_count,
                "file_size": file_size,
                "columns": columns,
                "column_types": column_types,
            }
        )
        if uploaded_at is not UNSET:
            field_dict["uploaded_at"] = uploaded_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dataset_upload_response_column_types import DatasetUploadResponseColumnTypes

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        slug = d.pop("slug")

        row_count = d.pop("row_count")

        file_size = d.pop("file_size")

        columns = cast(list[str], d.pop("columns"))

        column_types = DatasetUploadResponseColumnTypes.from_dict(d.pop("column_types"))

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

        dataset_upload_response = cls(
            id=id,
            name=name,
            slug=slug,
            row_count=row_count,
            file_size=file_size,
            columns=columns,
            column_types=column_types,
            uploaded_at=uploaded_at,
            updated_at=updated_at,
        )

        dataset_upload_response.additional_properties = d
        return dataset_upload_response

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

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.dashboard_detail_layout_type_0 import DashboardDetailLayoutType0


T = TypeVar("T", bound="DashboardDetail")


@_attrs_define
class DashboardDetail:
    """Full dashboard row.

    `widgets` and `layout` are JSONB blobs whose shape is defined by the
    dashboard editor / widget runtime. We accept them verbatim with
    `extra='allow'` covering any future top-level columns.

        Attributes:
            id (str):
            name (str):
            slug (str):
            description (None | str | Unset):
            widgets (list[Any] | Unset): Widget specs — shape is widget-runtime-defined.
            layout (DashboardDetailLayoutType0 | None | Unset): Layout JSONB — react-grid-layout shape, but accepted
                verbatim.
            sources (list[Any] | Unset): Plugin/dataset references; shape is dashboard-author-defined.
            created_by (None | str | Unset):
            created_at (None | str | Unset):
            updated_at (None | str | Unset):
    """

    id: str
    name: str
    slug: str
    description: None | str | Unset = UNSET
    widgets: list[Any] | Unset = UNSET
    layout: DashboardDetailLayoutType0 | None | Unset = UNSET
    sources: list[Any] | Unset = UNSET
    created_by: None | str | Unset = UNSET
    created_at: None | str | Unset = UNSET
    updated_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.dashboard_detail_layout_type_0 import DashboardDetailLayoutType0

        id = self.id

        name = self.name

        slug = self.slug

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        widgets: list[Any] | Unset = UNSET
        if not isinstance(self.widgets, Unset):
            widgets = self.widgets

        layout: dict[str, Any] | None | Unset
        if isinstance(self.layout, Unset):
            layout = UNSET
        elif isinstance(self.layout, DashboardDetailLayoutType0):
            layout = self.layout.to_dict()
        else:
            layout = self.layout

        sources: list[Any] | Unset = UNSET
        if not isinstance(self.sources, Unset):
            sources = self.sources

        created_by: None | str | Unset
        if isinstance(self.created_by, Unset):
            created_by = UNSET
        else:
            created_by = self.created_by

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

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
        if widgets is not UNSET:
            field_dict["widgets"] = widgets
        if layout is not UNSET:
            field_dict["layout"] = layout
        if sources is not UNSET:
            field_dict["sources"] = sources
        if created_by is not UNSET:
            field_dict["created_by"] = created_by
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dashboard_detail_layout_type_0 import DashboardDetailLayoutType0

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

        widgets = cast(list[Any], d.pop("widgets", UNSET))

        def _parse_layout(data: object) -> DashboardDetailLayoutType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                layout_type_0 = DashboardDetailLayoutType0.from_dict(data)

                return layout_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(DashboardDetailLayoutType0 | None | Unset, data)

        layout = _parse_layout(d.pop("layout", UNSET))

        sources = cast(list[Any], d.pop("sources", UNSET))

        def _parse_created_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_by = _parse_created_by(d.pop("created_by", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_updated_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        updated_at = _parse_updated_at(d.pop("updated_at", UNSET))

        dashboard_detail = cls(
            id=id,
            name=name,
            slug=slug,
            description=description,
            widgets=widgets,
            layout=layout,
            sources=sources,
            created_by=created_by,
            created_at=created_at,
            updated_at=updated_at,
        )

        dashboard_detail.additional_properties = d
        return dashboard_detail

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

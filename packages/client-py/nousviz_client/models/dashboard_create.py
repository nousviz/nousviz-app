from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.dashboard_create_layout_type_0 import DashboardCreateLayoutType0


T = TypeVar("T", bound="DashboardCreate")


@_attrs_define
class DashboardCreate:
    """
    Attributes:
        name (str):
        description (None | str | Unset):
        widgets (list[Any] | Unset):
        layout (DashboardCreateLayoutType0 | None | Unset):
        sources (list[Any] | Unset):
    """

    name: str
    description: None | str | Unset = UNSET
    widgets: list[Any] | Unset = UNSET
    layout: DashboardCreateLayoutType0 | None | Unset = UNSET
    sources: list[Any] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.dashboard_create_layout_type_0 import DashboardCreateLayoutType0

        name = self.name

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
        elif isinstance(self.layout, DashboardCreateLayoutType0):
            layout = self.layout.to_dict()
        else:
            layout = self.layout

        sources: list[Any] | Unset = UNSET
        if not isinstance(self.sources, Unset):
            sources = self.sources

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
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

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dashboard_create_layout_type_0 import DashboardCreateLayoutType0

        d = dict(src_dict)
        name = d.pop("name")

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        widgets = cast(list[Any], d.pop("widgets", UNSET))

        def _parse_layout(data: object) -> DashboardCreateLayoutType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                layout_type_0 = DashboardCreateLayoutType0.from_dict(data)

                return layout_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(DashboardCreateLayoutType0 | None | Unset, data)

        layout = _parse_layout(d.pop("layout", UNSET))

        sources = cast(list[Any], d.pop("sources", UNSET))

        dashboard_create = cls(
            name=name,
            description=description,
            widgets=widgets,
            layout=layout,
            sources=sources,
        )

        dashboard_create.additional_properties = d
        return dashboard_create

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

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.alert_test_response_triggered_rows_type_0_item import AlertTestResponseTriggeredRowsType0Item


T = TypeVar("T", bound="AlertTestResponse")


@_attrs_define
class AlertTestResponse:
    """POST /api/alerts/{alert_id}/test — dry-run evaluation result.

    `error` is set when the alert worker module isn't importable or the
    evaluation raised; otherwise `fired` + `rows_checked` + `triggered_rows`
    describe the test outcome.

        Attributes:
            alert_id (str):
            fired (bool | None | Unset):
            message (None | str | Unset):
            rows_checked (int | None | Unset):
            triggered_rows (list[AlertTestResponseTriggeredRowsType0Item] | None | Unset): Up to 5 rows that would have
                triggered.
            error (None | str | Unset):
    """

    alert_id: str
    fired: bool | None | Unset = UNSET
    message: None | str | Unset = UNSET
    rows_checked: int | None | Unset = UNSET
    triggered_rows: list[AlertTestResponseTriggeredRowsType0Item] | None | Unset = UNSET
    error: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        alert_id = self.alert_id

        fired: bool | None | Unset
        if isinstance(self.fired, Unset):
            fired = UNSET
        else:
            fired = self.fired

        message: None | str | Unset
        if isinstance(self.message, Unset):
            message = UNSET
        else:
            message = self.message

        rows_checked: int | None | Unset
        if isinstance(self.rows_checked, Unset):
            rows_checked = UNSET
        else:
            rows_checked = self.rows_checked

        triggered_rows: list[dict[str, Any]] | None | Unset
        if isinstance(self.triggered_rows, Unset):
            triggered_rows = UNSET
        elif isinstance(self.triggered_rows, list):
            triggered_rows = []
            for triggered_rows_type_0_item_data in self.triggered_rows:
                triggered_rows_type_0_item = triggered_rows_type_0_item_data.to_dict()
                triggered_rows.append(triggered_rows_type_0_item)

        else:
            triggered_rows = self.triggered_rows

        error: None | str | Unset
        if isinstance(self.error, Unset):
            error = UNSET
        else:
            error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "alert_id": alert_id,
            }
        )
        if fired is not UNSET:
            field_dict["fired"] = fired
        if message is not UNSET:
            field_dict["message"] = message
        if rows_checked is not UNSET:
            field_dict["rows_checked"] = rows_checked
        if triggered_rows is not UNSET:
            field_dict["triggered_rows"] = triggered_rows
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.alert_test_response_triggered_rows_type_0_item import AlertTestResponseTriggeredRowsType0Item

        d = dict(src_dict)
        alert_id = d.pop("alert_id")

        def _parse_fired(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        fired = _parse_fired(d.pop("fired", UNSET))

        def _parse_message(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message = _parse_message(d.pop("message", UNSET))

        def _parse_rows_checked(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        rows_checked = _parse_rows_checked(d.pop("rows_checked", UNSET))

        def _parse_triggered_rows(data: object) -> list[AlertTestResponseTriggeredRowsType0Item] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                triggered_rows_type_0 = []
                _triggered_rows_type_0 = data
                for triggered_rows_type_0_item_data in _triggered_rows_type_0:
                    triggered_rows_type_0_item = AlertTestResponseTriggeredRowsType0Item.from_dict(
                        triggered_rows_type_0_item_data
                    )

                    triggered_rows_type_0.append(triggered_rows_type_0_item)

                return triggered_rows_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[AlertTestResponseTriggeredRowsType0Item] | None | Unset, data)

        triggered_rows = _parse_triggered_rows(d.pop("triggered_rows", UNSET))

        def _parse_error(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        error = _parse_error(d.pop("error", UNSET))

        alert_test_response = cls(
            alert_id=alert_id,
            fired=fired,
            message=message,
            rows_checked=rows_checked,
            triggered_rows=triggered_rows,
            error=error,
        )

        alert_test_response.additional_properties = d
        return alert_test_response

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

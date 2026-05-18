from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.ssl_block import SSLBlock


T = TypeVar("T", bound="SslSetupResponse")


@_attrs_define
class SslSetupResponse:
    """POST /api/admin/ssl/setup — Let's Encrypt provisioning result.

    On success, `ssl` carries the new SSL config (mirrors `_get_ssl_status`).
    On failure, `reason` carries a machine-readable classification (e.g.
    'timeout', 'dns_no_match') and `error` carries the human-readable message.

        Attributes:
            ok (bool):
            output (None | str | Unset):
            ssl (None | SSLBlock | Unset):
            reason (None | str | Unset): Failure classification when ok=false (e.g. 'timeout', 'dns_no_match').
            error (None | str | Unset):
    """

    ok: bool
    output: None | str | Unset = UNSET
    ssl: None | SSLBlock | Unset = UNSET
    reason: None | str | Unset = UNSET
    error: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.ssl_block import SSLBlock

        ok = self.ok

        output: None | str | Unset
        if isinstance(self.output, Unset):
            output = UNSET
        else:
            output = self.output

        ssl: dict[str, Any] | None | Unset
        if isinstance(self.ssl, Unset):
            ssl = UNSET
        elif isinstance(self.ssl, SSLBlock):
            ssl = self.ssl.to_dict()
        else:
            ssl = self.ssl

        reason: None | str | Unset
        if isinstance(self.reason, Unset):
            reason = UNSET
        else:
            reason = self.reason

        error: None | str | Unset
        if isinstance(self.error, Unset):
            error = UNSET
        else:
            error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ok": ok,
            }
        )
        if output is not UNSET:
            field_dict["output"] = output
        if ssl is not UNSET:
            field_dict["ssl"] = ssl
        if reason is not UNSET:
            field_dict["reason"] = reason
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.ssl_block import SSLBlock

        d = dict(src_dict)
        ok = d.pop("ok")

        def _parse_output(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        output = _parse_output(d.pop("output", UNSET))

        def _parse_ssl(data: object) -> None | SSLBlock | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                ssl_type_0 = SSLBlock.from_dict(data)

                return ssl_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SSLBlock | Unset, data)

        ssl = _parse_ssl(d.pop("ssl", UNSET))

        def _parse_reason(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        reason = _parse_reason(d.pop("reason", UNSET))

        def _parse_error(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        error = _parse_error(d.pop("error", UNSET))

        ssl_setup_response = cls(
            ok=ok,
            output=output,
            ssl=ssl,
            reason=reason,
            error=error,
        )

        ssl_setup_response.additional_properties = d
        return ssl_setup_response

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

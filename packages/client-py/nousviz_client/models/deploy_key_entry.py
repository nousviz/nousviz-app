from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.deploy_key_creator import DeployKeyCreator


T = TypeVar("T", bound="DeployKeyEntry")


@_attrs_define
class DeployKeyEntry:
    """A single deploy_keys row as returned by GET /api/settings/deploy-keys.

    Attributes:
        id (str):
        name (str):
        host (str):
        public_key (str):
        repo_url (None | str | Unset):
        fingerprint (None | str | Unset):
        created_at (None | str | Unset):
        created_by (DeployKeyCreator | None | Unset): The actor who created this key. Null if the user has been deleted.
    """

    id: str
    name: str
    host: str
    public_key: str
    repo_url: None | str | Unset = UNSET
    fingerprint: None | str | Unset = UNSET
    created_at: None | str | Unset = UNSET
    created_by: DeployKeyCreator | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.deploy_key_creator import DeployKeyCreator

        id = self.id

        name = self.name

        host = self.host

        public_key = self.public_key

        repo_url: None | str | Unset
        if isinstance(self.repo_url, Unset):
            repo_url = UNSET
        else:
            repo_url = self.repo_url

        fingerprint: None | str | Unset
        if isinstance(self.fingerprint, Unset):
            fingerprint = UNSET
        else:
            fingerprint = self.fingerprint

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        created_by: dict[str, Any] | None | Unset
        if isinstance(self.created_by, Unset):
            created_by = UNSET
        elif isinstance(self.created_by, DeployKeyCreator):
            created_by = self.created_by.to_dict()
        else:
            created_by = self.created_by

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "host": host,
                "public_key": public_key,
            }
        )
        if repo_url is not UNSET:
            field_dict["repo_url"] = repo_url
        if fingerprint is not UNSET:
            field_dict["fingerprint"] = fingerprint
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if created_by is not UNSET:
            field_dict["created_by"] = created_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.deploy_key_creator import DeployKeyCreator

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        host = d.pop("host")

        public_key = d.pop("public_key")

        def _parse_repo_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        repo_url = _parse_repo_url(d.pop("repo_url", UNSET))

        def _parse_fingerprint(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        fingerprint = _parse_fingerprint(d.pop("fingerprint", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_created_by(data: object) -> DeployKeyCreator | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                created_by_type_0 = DeployKeyCreator.from_dict(data)

                return created_by_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(DeployKeyCreator | None | Unset, data)

        created_by = _parse_created_by(d.pop("created_by", UNSET))

        deploy_key_entry = cls(
            id=id,
            name=name,
            host=host,
            public_key=public_key,
            repo_url=repo_url,
            fingerprint=fingerprint,
            created_at=created_at,
            created_by=created_by,
        )

        deploy_key_entry.additional_properties = d
        return deploy_key_entry

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

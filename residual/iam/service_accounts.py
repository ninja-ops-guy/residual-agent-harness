"""Service accounts for bots, CI/CD pipelines, and automated systems.

Implements ENT1-R5: service accounts have scoped permissions (never
admin — module installation and policy modification are forbidden),
support credential rotation, emit observations for every action, and
are distinguishable from human accounts in receipts (subject_type is
"service" on every observation and receipt).
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field

from ..core import ContractError, identifier
from .events import EVENT_ACCESS_DENIED, EVENT_SERVICE_ACTION, EventLog, SUBJECT_SERVICE
from .rbac import (
    PERMISSION_MODULE_INSTALLATION,
    PERMISSION_POLICY_MODIFICATION,
    Permission,
)

#: Permissions a service account can never hold (never admin). ENT1-R5.
FORBIDDEN_SERVICE_PERMISSIONS = frozenset({
    PERMISSION_MODULE_INSTALLATION,
    PERMISSION_POLICY_MODIFICATION,
})


@dataclass(frozen=True)
class ServiceAccount:
    """A non-human identity with scoped permissions. Implements ENT1-R5."""

    account_id: str
    name: str
    owner_id: str
    permissions: frozenset[Permission] = field(default_factory=frozenset)
    credential_generation: int = 1

    def __post_init__(self):
        identifier(self.account_id)
        if not isinstance(self.name, str) or not self.name.strip():
            raise ContractError("service account name is required")
        identifier(self.owner_id)
        if not isinstance(self.permissions, frozenset) or any(
                not isinstance(p, Permission) for p in self.permissions):
            raise ContractError("service account permissions must be a frozenset of Permission")
        if any(p.category in FORBIDDEN_SERVICE_PERMISSIONS for p in self.permissions):
            raise ContractError("service accounts can never hold admin permissions")
        if type(self.credential_generation) is not int or self.credential_generation < 1:
            raise ContractError("credential generation must be a positive integer")


class ServiceAccountManager:
    """Creates, authenticates, and rotates service accounts. ENT1-R5."""

    def __init__(self, log: EventLog):
        if not isinstance(log, EventLog):
            raise ContractError("log must be an EventLog")
        self._log = log
        self._accounts: dict[str, ServiceAccount] = {}
        self._credential_hashes: dict[str, str] = {}  # credential_hash -> account_id

    @staticmethod
    def _hash_credential(credential: str) -> str:
        if not isinstance(credential, str) or not credential:
            raise ContractError("credential must be a non-empty string")
        return hashlib.sha256(("residual.iam.sa\n" + credential).encode("utf-8")).hexdigest()

    def create(
        self,
        name: str,
        owner_id: str,
        permissions: frozenset[Permission] | set[Permission],
    ) -> tuple[ServiceAccount, str]:
        """Create a service account and its initial credential. ENT1-R5.

        Raises ContractError if admin permissions are requested.
        """
        if not isinstance(name, str) or not name.strip():
            raise ContractError("service account name is required")
        identifier(owner_id)
        account_id = "svc-" + secrets.token_hex(6)
        account = ServiceAccount(
            account_id=account_id,
            name=name,
            owner_id=owner_id,
            permissions=frozenset(permissions),
        )
        credential = "svckey-" + secrets.token_urlsafe(24)
        self._accounts[account_id] = account
        self._credential_hashes[self._hash_credential(credential)] = account_id
        return account, credential

    def authenticate(self, credential: str) -> ServiceAccount:
        """Resolve a credential to a service account. Implements ENT1-R5."""
        account_id = self._credential_hashes.get(self._hash_credential(credential))
        if account_id is None:
            raise ContractError("invalid or rotated service account credential")
        return self._accounts[account_id]

    def rotate(self, account_id: str) -> tuple[ServiceAccount, str]:
        """Rotate credentials: the old credential stops working
        immediately. Implements ENT1-R5 (credential rotation)."""
        if account_id not in self._accounts:
            raise ContractError("unknown service account")
        account = self._accounts[account_id]
        rotated = ServiceAccount(
            account_id=account.account_id,
            name=account.name,
            owner_id=account.owner_id,
            permissions=account.permissions,
            credential_generation=account.credential_generation + 1,
        )
        for cred_hash, acc_id in list(self._credential_hashes.items()):
            if acc_id == account_id:
                del self._credential_hashes[cred_hash]
        credential = "svckey-" + secrets.token_urlsafe(24)
        self._credential_hashes[self._hash_credential(credential)] = account_id
        self._accounts[account_id] = rotated
        return rotated, credential

    def authorize(self, account: ServiceAccount, category: str, scope: str, source_ip: str) -> bool:
        """Authorize an action and emit an observation for it. ENT1-R5:
        every service-account action is observed, and receipts mark the
        subject as a service account (distinguishable from humans)."""
        if not isinstance(account, ServiceAccount):
            raise ContractError("expected a ServiceAccount")
        allowed = any(p.grants(category, scope) for p in account.permissions)
        self._log.record(
            EVENT_SERVICE_ACTION if allowed else EVENT_ACCESS_DENIED,
            account.account_id,
            source_ip,
            "allow" if allowed else "deny",
            subject_type=SUBJECT_SERVICE,
            details={"category": category, "scope": scope, "owner": account.owner_id},
        )
        return allowed

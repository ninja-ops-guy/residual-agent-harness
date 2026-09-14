"""Enterprise Identity and Access Management (SPEC-ENT-001).

Implements ENT1-R1 through ENT1-R8:

- ENT1-R1: SAML 2.0 and OIDC authentication (residual.iam.saml,
  residual.iam.oidc) with presets for Okta, Azure AD (Entra ID),
  Ping Identity, Auth0, and OneLogin.
- ENT1-R2: Role-Based Access Control with fine-grained permissions
  (residual.iam.rbac).
- ENT1-R3: Attribute-Based Access Control over IdP attributes
  (residual.iam.abac).
- ENT1-R4: Just-In-Time access elevation with pre-authorization,
  automatic expiry, observation, and receipts (residual.iam.jit).
- ENT1-R5: Service accounts with scoped permissions, credential
  rotation, per-action observations, and service-marked receipts
  (residual.iam.service_accounts).
- ENT1-R6: Observation + receipt of all authentication events
  (residual.iam.events).
- ENT1-R7: MFA enforcement, IdP-delegated or local TOTP, mandatory for
  privileged actions (residual.iam.mfa).
- ENT1-R8: Enterprise session management with configurable timeouts,
  concurrent limits, IP restrictions, and immediate revocation
  (residual.iam.sessions).
"""
from . import abac, events, jit, mfa, oidc, rbac, saml, service_accounts, sessions
from .abac import ABACEvaluator, ABACPolicy, Condition, UserAttributes
from .events import EventLog, EventReceipt, Observation
from .jit import JITManager
from .mfa import MFAManager
from .oidc import OIDCClient, OIDCSettings
from .rbac import Permission, Role, RoleRegistry
from .saml import Identity, SAMLSettings
from .service_accounts import ServiceAccount, ServiceAccountManager
from .sessions import Session, SessionManager, SessionPolicy

__all__ = [
    "abac", "events", "jit", "mfa", "oidc", "rbac", "saml", "service_accounts", "sessions",
    "ABACEvaluator", "ABACPolicy", "Condition", "UserAttributes",
    "EventLog", "EventReceipt", "Observation",
    "JITManager", "MFAManager",
    "OIDCClient", "OIDCSettings",
    "Permission", "Role", "RoleRegistry",
    "Identity", "SAMLSettings",
    "ServiceAccount", "ServiceAccountManager",
    "Session", "SessionManager", "SessionPolicy",
]

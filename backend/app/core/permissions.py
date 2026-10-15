"""Role -> permission map. Enforced by server-side dependencies, never by the UI alone.

Roles are data-driven in the database, but the default permission set lives here so
it is versioned and testable. Municipal org structure is not yet known: adjust here.
"""
from enum import StrEnum


class Role(StrEnum):
    SUPER_ADMIN = "super_admin"
    MUNICIPAL_ADMIN = "municipal_admin"
    WATER_OFFICER = "water_officer"
    WARD_OFFICER = "ward_officer"
    VALVE_OPERATOR = "valve_operator"


# Lower number = more privileged.
RANK = {Role.SUPER_ADMIN: 1, Role.MUNICIPAL_ADMIN: 2, Role.WATER_OFFICER: 3,
        Role.WARD_OFFICER: 4, Role.VALVE_OPERATOR: 5}

# Roles that see every ward without needing assignments.
ALL_JURISDICTION = {Role.SUPER_ADMIN, Role.MUNICIPAL_ADMIN}

PERMISSIONS: dict[Role, set[str]] = {
    Role.SUPER_ADMIN: {"users.view", "users.manage", "wards.view", "wards.manage",
                       "audit.view", "settings.manage", "schedules.create",
                       "schedules.approve", "gis.manage", "reports.view"},
    Role.MUNICIPAL_ADMIN: {"users.view", "users.manage", "wards.view", "wards.manage",
                           "schedules.approve", "gis.manage", "reports.view"},
    Role.WATER_OFFICER: {"wards.view", "schedules.create", "reports.view"},
    Role.WARD_OFFICER: {"wards.view", "reports.view"},
    Role.VALVE_OPERATOR: {"wards.view", "sessions.operate"},
}


def has_permission(role: str, perm: str) -> bool:
    try:
        return perm in PERMISSIONS[Role(role)]
    except (ValueError, KeyError):
        return False


def can_manage_role(actor_role: str, target_role: str) -> bool:
    """An actor may only create/modify users strictly below their own rank
    (Super Administrators may manage any role)."""
    a, t = Role(actor_role), Role(target_role)
    if a == Role.SUPER_ADMIN:
        return True
    return RANK[a] < RANK[t]

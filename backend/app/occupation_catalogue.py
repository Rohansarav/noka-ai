"""Short-lived immutable public evidence cache; never contains sessions or profile data."""
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from weakref import WeakKeyDictionary
from sqlalchemy import select
from backend.app.models import Role, RoleSkill, Skill, RoleTechnology

TTL_SECONDS = 30
_cache = WeakKeyDictionary()
_skills_cache = WeakKeyDictionary()
_lock = RLock()


@dataclass(frozen=True)
class Occupation:
    id: str
    title: str
    description: str
    occupation_code: str
    source_id: str


@dataclass(frozen=True)
class Requirement:
    role_id: str
    skill_id: str
    required_importance: float
    source_id: str


@dataclass(frozen=True)
class CatalogueSkill:
    id: str
    canonical_name: str
    category: str


def invalidate_catalogue(bind):
    with _lock:
        _cache.pop(bind, None)
        _skills_cache.pop(bind, None)


@dataclass(frozen=True)
class PublishedSkill:
    id: str
    canonical_name: str
    aliases: tuple
    category: str
    source_id: str


@dataclass(frozen=True)
class TechnologyAssociation:
    role_id: str
    skill_id: str
    source_id: str
    hot_technology: bool
    in_demand: bool


def skill_evidence(db):
    """Public concepts and unweighted software associations, never private profile levels."""
    bind=db.get_bind()
    with _lock:
        entry=_skills_cache.get(bind)
        if entry and monotonic()-entry[0]<TTL_SECONDS:return entry[1],entry[2]
        skills={s.id:PublishedSkill(s.id,s.canonical_name,tuple(s.aliases),s.category,s.source_id) for s in db.execute(select(Skill.id,Skill.canonical_name,Skill.aliases,Skill.category,Skill.source_id))}
        associations=tuple(TechnologyAssociation(*row) for row in db.execute(select(RoleTechnology.role_id,RoleTechnology.skill_id,RoleTechnology.source_id,RoleTechnology.hot_technology,RoleTechnology.in_demand)))
        _skills_cache[bind]=(monotonic(),skills,associations)
        return skills,associations


def occupation_evidence(db):
    """Avoid retransferring 31,850 repeated public mappings for each private request.

    Primitive frozen records cannot expire, lazy-load SQL or expose another user's context.
    The cache is isolated per database and refreshed after imports or at most 30 seconds.
    """
    bind = db.get_bind()
    with _lock:
        entry = _cache.get(bind)
        if entry and monotonic()-entry[0] < TTL_SECONDS:
            return entry[1], entry[2]
        roles = tuple(Occupation(*row) for row in db.execute(select(Role.id,Role.title,Role.description,Role.occupation_code,Role.source_id).order_by(Role.id)))
        skills = {s.id:CatalogueSkill(s.id,s.canonical_name,s.category) for s in db.execute(select(Skill.id,Skill.canonical_name,Skill.category))}
        requirements = tuple((Requirement(*row),skills[row.skill_id]) for row in db.execute(select(RoleSkill.role_id,RoleSkill.skill_id,RoleSkill.required_importance,RoleSkill.source_id)))
        _cache[bind] = (monotonic(),roles,requirements)
        return roles, requirements

"""Persistence layer.

The Event table is the source of truth (append-only). Agent / Relationship tables are
*projections* — derived, rebuildable views kept in sync as events are appended. This is
the event-sourcing backbone described in the plan.
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String

import json
from sqlalchemy.types import TypeDecorator

from .database import Base


class SafeJSON(TypeDecorator):
    """Custom JSON type that guarantees loaded values are parsed Python dicts/lists,
    even if the underlying DB driver/dialect returns them as raw strings.
    """
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return {}
        return value


def _now():
    return datetime.now(timezone.utc)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    day = Column(Integer, nullable=False, index=True)
    tick = Column(Integer, nullable=False)
    type = Column(String, nullable=False, index=True)
    agent_id = Column(Integer, index=True)        # actor
    target_id = Column(Integer, index=True)       # other party, if any
    payload = Column(SafeJSON, default=dict)
    importance = Column(Float, default=0.1)
    created_at = Column(DateTime, default=_now)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    background = Column(String)
    personality = Column(String)
    occupation = Column(String)
    faction = Column(String)
    wealth = Column(Float, default=100.0)
    happiness = Column(Float, default=50.0)
    energy = Column(Float, default=100.0)
    x = Column(Integer)
    y = Column(Integer)
    tier = Column(Integer, default=1)


class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    a_id = Column(Integer, index=True, nullable=False)
    b_id = Column(Integer, index=True, nullable=False)
    trust = Column(Float, default=0.0)
    friendship = Column(Float, default=0.0)
    rivalry = Column(Float, default=0.0)


class SimState(Base):
    """Single-row table tracking the clock."""
    __tablename__ = "sim_state"

    id = Column(Integer, primary_key=True, default=1)
    day = Column(Integer, default=0)
    tick = Column(Integer, default=0)
    kitty_pool = Column(Float, default=100.0)


class Business(Base):
    """A venture founded by an agent. Employs others, earns revenue, can go bankrupt."""
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    btype = Column(String)                  # market_node | data_den | clinic | bar ...
    owner_id = Column(Integer, index=True)
    x = Column(Integer)
    y = Column(Integer)
    capital = Column(Float, default=100.0)
    employees = Column(SafeJSON, default=list)  # list of agent ids
    day_founded = Column(Integer, default=0)
    status = Column(String, default="open")  # open | bankrupt


class Plan(Base):
    """A Tier-2 agent's current multi-step plan, produced by the LLM planner."""
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, index=True, nullable=False)
    day_created = Column(Integer, nullable=False)
    goal = Column(String, nullable=False)
    steps = Column(SafeJSON, default=list)     # [{"action": ..., "note": ...}, ...]
    step_index = Column(Integer, default=0)
    status = Column(String, default="active")  # active | done
    source = Column(String, default="llm")     # llm | fallback

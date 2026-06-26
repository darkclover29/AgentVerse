from typing import Any, Optional

from pydantic import BaseModel


class AgentOut(BaseModel):
    id: int
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    background: Optional[str] = None
    personality: Optional[str] = None
    occupation: Optional[str] = None
    faction: Optional[str] = None
    wealth: float
    happiness: float
    energy: float
    x: int
    y: int
    tier: int
    dest_x: Optional[int] = None
    dest_y: Optional[int] = None

    class Config:
        from_attributes = True


class EventOut(BaseModel):
    id: int
    day: int
    tick: int
    type: str
    agent_id: Optional[int] = None
    target_id: Optional[int] = None
    payload: dict[str, Any] = {}
    importance: float

    class Config:
        from_attributes = True


class RelationshipOut(BaseModel):
    a_id: int
    b_id: int
    trust: float
    friendship: float
    rivalry: float

    class Config:
        from_attributes = True


class TileOut(BaseModel):
    x: int
    y: int
    type: str


class WorldOut(BaseModel):
    grid_size: int
    tiles: list[TileOut]


class ClockOut(BaseModel):
    day: int
    tick: int


class StepRequest(BaseModel):
    ticks: int = 1


class BusinessOut(BaseModel):
    id: int
    name: str
    btype: Optional[str] = None
    owner: str
    owner_id: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None
    capital: float
    employees: int
    status: str
    day_founded: int


class HealthOut(BaseModel):
    status: str
    day: int
    tick: int
    agents: int
    ollama: bool
    chroma: bool


class StatusOut(BaseModel):
    ollama: bool
    chroma: bool
    model: str

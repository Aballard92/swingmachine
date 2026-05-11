from __future__ import annotations

from typing import Annotated, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class ImmutableModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, defer_build=True)


Percent: TypeAlias = Annotated[float, Field(ge=0.0, le=1.0)]
NonNegativeFloat: TypeAlias = Annotated[float, Field(ge=0.0)]
PositiveFloat: TypeAlias = Annotated[float, Field(gt=0.0)]
NonNegativeInt: TypeAlias = Annotated[int, Field(ge=0)]
PositiveInt: TypeAlias = Annotated[int, Field(gt=0)]

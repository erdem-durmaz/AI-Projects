from pydantic import BaseModel, Field, field_validator

from app.config import DAYS


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list = Field(default_factory=list)


class FavRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class ReorderRequest(BaseModel):
    names: list[str]


class PlanDayRequest(BaseModel):
    day: str
    meal: str = Field(..., min_length=1, max_length=200)

    @field_validator("day")
    @classmethod
    def validate_day(cls, v: str) -> str:
        if v not in DAYS:
            raise ValueError(f"Geçersiz gün: {v}")
        return v


class PlanClearDayRequest(BaseModel):
    day: str

    @field_validator("day")
    @classmethod
    def validate_day(cls, v: str) -> str:
        if v not in DAYS:
            raise ValueError(f"Geçersiz gün: {v}")
        return v


class SearchRequest(BaseModel):
    query: str = Field(default="", max_length=200)


class RecipeRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=2000)


class RecipeByNameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class PreferencesRequest(BaseModel):
    person_count: str = Field(default="3", max_length=10)
    meal_type: str = Field(default="Akşam yemeği", max_length=100)
    style: str = Field(default="", max_length=500)
    preferences: str = Field(default="", max_length=1000)
    dislikes: str = Field(default="", max_length=1000)


def _lines_to_list(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


class CustomRecipeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    ingredients: str = Field(default="", max_length=8000)
    steps: str = Field(default="", max_length=12000)
    time: str = Field(default="", max_length=100)
    servings: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=2000)

    def parsed_ingredients(self) -> list[str]:
        return _lines_to_list(self.ingredients)

    def parsed_steps(self) -> list[str]:
        return _lines_to_list(self.steps)


class CustomRecipeUpdateRequest(CustomRecipeRequest):
    id: int = Field(..., ge=1)


class CustomRecipeDeleteRequest(BaseModel):
    id: int = Field(..., ge=1)

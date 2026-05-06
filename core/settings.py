from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MongoDBCollections(BaseModel):
    film_ratings: str = "film_ratings"
    reviews: str = "reviews"
    review_likes: str = "review_likes"
    bookmarks: str = "bookmarks"


class MongoDBSettings(BaseModel):
    host: str = "localhost"
    port: int = 27017
    db: str = "ugc_db"
    test_db: str = "ugc_test_db"
    collections: MongoDBCollections = Field(default_factory=MongoDBCollections)

    @property
    def url(self) -> str:
        return f"mongodb://{self.host}:{self.port}"


class AuthSettings(BaseModel):
    service_url: str = "http://localhost:8001"
    introspect_path: str = "/api/v1/auth/introspect"

    @property
    def introspect_url(self) -> str:
        return f"{self.service_url}{self.introspect_path}"


class Settings(BaseSettings):
    mongodb: MongoDBSettings = Field(default_factory=MongoDBSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )


settings = Settings()

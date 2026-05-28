from dataclasses import dataclass, field


@dataclass
class CollectorResult:
    source: str
    reviews: list[dict] = field(default_factory=list)   # {rating, text, age_days?}
    jobs: list[dict] = field(default_factory=list)      # {title, area, url, age_days?}
    news: list[dict] = field(default_factory=list)      # {title, url, source, published_at, categories[]}
    meta: dict = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

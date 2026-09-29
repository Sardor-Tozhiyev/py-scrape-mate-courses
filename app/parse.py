import re
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import TypeVar, Generic
from urllib.parse import urljoin

import requests
from bs4 import Tag, BeautifulSoup


BASE_URL = "https://mate.academy"
CARD_SELECTOR = "[class*='ProfessionCard_card']"

T = TypeVar("T")


@dataclass
class Course:
    name: str
    short_description: str
    duration: str
    modules_count: int
    topics_count: int


class FieldParser(ABC, Generic[T]):
    @property
    @abstractmethod
    def selector(self) -> str:
        pass

    def get_text(self, element: Tag) -> str:
        found = element.select_one(self.selector)
        if found is None:
            raise ValueError(f"No text in {self.selector}")
        return found.text.strip()

    @abstractmethod
    def parse(self, element: Tag) -> T:
        pass


class TextParser(FieldParser[str], ABC):
    def parse(self, element: Tag) -> str:
        return self.get_text(element)


class CountParser(FieldParser[int], ABC):
    def parse(self, element: Tag) -> int:
        text = self.get_text(element)
        match = re.search(r"\d+", text)
        if match is None:
            raise ValueError(f"No number in '{text}' for {self.selector}")
        return int(match.group())


class NameParser(TextParser):
    selector = "[class*='ProfessionCard_title']"


class ShortDescriptionParser(TextParser):
    selector = "[class*='ProfessionCard_description']"


class DurationParser(TextParser):
    selector = "[class*='ProfessionCard_duration']"


class ModulesParser(CountParser):
    selector = "[class*='CourseModulesList_topicsCount']"

    def parse(self, element: Tag) -> int:
        return len(element.select(self.selector))


class TopicsParser(CountParser):
    selector = "[class*='CourseModulesList_topicsCount']"

    def parse(self, element: Tag) -> int:
        total = 0
        for found in element.select(self.selector):
            match = re.search(r"\d+", found.text)
            if match is None:
                raise ValueError(
                    f"No number in '{found.text}' for {self.selector}"
                )
            total += int(match.group())
        return total


def fetch_soup(url: str) -> BeautifulSoup:
    page = requests.get(url, timeout=10).content
    return BeautifulSoup(page, "html.parser")


def get_detail_url(card: Tag) -> str:
    href = card.get("href")
    if href is None:
        raise ValueError("Course link is not found in card")
    return urljoin(BASE_URL, str(href))


class CourseParser:
    def __init__(self) -> None:
        self.name_parser = NameParser()
        self.description_parser = ShortDescriptionParser()
        self.duration_parser = DurationParser()
        self.modules_parser = ModulesParser()
        self.topics_parser = TopicsParser()

    def parse(self, card: Tag) -> Course:
        detail_soup = fetch_soup(get_detail_url(card))

        return Course(
            name=self.name_parser.parse(card),
            short_description=self.description_parser.parse(card),
            duration=self.duration_parser.parse(card),
            modules_count=self.modules_parser.parse(detail_soup),
            topics_count=self.topics_parser.parse(detail_soup),
        )


def get_all_courses() -> list[Course]:
    soup = fetch_soup(BASE_URL)
    parser = CourseParser()
    return [parser.parse(card) for card in soup.select(CARD_SELECTOR)]

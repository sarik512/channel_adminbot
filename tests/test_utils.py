import pytest
from utils import parse_title_input, generate_tag


def test_parse_valid():
    title, season, episode = parse_title_input("Боевой континет 1 12")
    assert title == "Боевой континет"
    assert season == 1
    assert episode == 12


def test_parse_title_with_spaces():
    title, s, e = parse_title_input("  Мое  Аниме  2  3  ")
    assert title == "Мое Аниме"
    assert s == 2
    assert e == 3


def test_parse_invalid():
    with pytest.raises(ValueError):
        parse_title_input("NoNumbersHere")


def test_generate_tag():
    assert generate_tag("Боевой континет") == "#Боевой_континет"
    assert generate_tag("  My   Anime  ") == "#My_Anime"

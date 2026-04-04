from __future__ import annotations

import random
from typing import Any

from faker import Faker

RACES = [
    "Black",
    "White",
    "Asian",
    "Latino",
    "Middle Eastern",
    "Mixed",
    "Indigenous",
    "Pacific Islander",
]
CAREERS = [
    "Software Engineer",
    "Nurse",
    "Teacher",
    "Electrician",
    "Designer",
    "Mechanic",
    "Analyst",
    "Chef",
]
SCHOOLS = [
    "University Student",
    "Community College Student",
    "Trade School Student",
    "High School Senior",
    "Graduate Student",
]

COUNTRY_TO_LOCALE = {
    "United States": "en_US",
    "Canada": "en_CA",
    "Mexico": "es_MX",
    "Cuba": "es_MX",
    "Panama": "es_MX",
    "Colombia": "es_CO",
    "Peru": "es_MX",
    "Ecuador": "es_MX",
    "Brazil": "pt_BR",
    "Argentina": "es_AR",
    "Chile": "es_CL",
    "Uruguay": "es_MX",
    "United Kingdom": "en_GB",
    "Ireland": "en_IE",
    "France": "fr_FR",
    "Germany": "de_DE",
    "Spain": "es_ES",
    "Portugal": "pt_PT",
    "Italy": "it_IT",
    "Greece": "en_US",
    "Poland": "pl_PL",
    "Czechia": "cs_CZ",
    "Austria": "de_AT",
    "Hungary": "hu_HU",
    "Netherlands": "nl_NL",
    "Belgium": "nl_BE",
    "Denmark": "da_DK",
    "Sweden": "sv_SE",
    "Norway": "no_NO",
    "Finland": "fi_FI",
    "Iceland": "en_GB",
    "Turkey": "tr_TR",
    "Romania": "ro_RO",
    "Bulgaria": "en_US",
    "Ukraine": "en_US",
    "Russia": "en_US",
    "Egypt": "en_US",
    "Nigeria": "en_NG",
    "Kenya": "en_US",
    "Ethiopia": "en_US",
    "Ghana": "en_US",
    "Senegal": "fr_FR",
    "Morocco": "fr_FR",
    "Algeria": "fr_FR",
    "Tunisia": "fr_FR",
    "Libya": "en_US",
    "Sudan": "en_US",
    "Rwanda": "fr_FR",
    "Uganda": "en_GB",
    "Tanzania": "en_US",
    "Mozambique": "pt_BR",
    "Zimbabwe": "en_GB",
    "Zambia": "en_GB",
    "South Africa": "en_ZA",
    "Namibia": "en_ZA",
    "Botswana": "en_ZA",
    "United Arab Emirates": "en_US",
    "Saudi Arabia": "en_US",
    "Qatar": "en_US",
    "Kuwait": "en_US",
    "Oman": "en_US",
    "Bahrain": "en_US",
    "Jordan": "en_US",
    "Lebanon": "fr_FR",
    "Israel": "en_US",
    "Iraq": "en_US",
    "Iran": "en_US",
    "India": "en_IN",
    "Bangladesh": "en_IN",
    "Pakistan": "en_IN",
    "Sri Lanka": "en_IN",
    "Nepal": "en_IN",
    "Japan": "en_US",
    "South Korea": "en_US",
    "China": "en_US",
    "Taiwan": "en_US",
    "Mongolia": "en_US",
    "Indonesia": "id_ID",
    "Singapore": "en_SG",
    "Malaysia": "ms_MY",
    "Thailand": "en_US",
    "Vietnam": "vi_VN",
    "Philippines": "tl_PH",
    "Cambodia": "fr_FR",
    "Myanmar": "en_US",
    "Australia": "en_AU",
    "New Zealand": "en_NZ",
    "Fiji": "en_NZ",
    "Papua New Guinea": "en_AU",
}

REGION_FALLBACK = {
    "North America": "en_US",
    "South America": "es_MX",
    "Europe": "en_GB",
    "Africa": "en_ZA",
    "Middle East": "en_US",
    "South Asia": "en_IN",
    "East Asia": "en_US",
    "Southeast Asia": "id_ID",
    "Oceania": "en_AU",
}


def get_ethnicity(country: str) -> str:
    c = country.lower()
    if c in [
        "china",
        "japan",
        "south korea",
        "taiwan",
        "mongolia",
        "vietnam",
        "thailand",
        "cambodia",
        "myanmar",
        "indonesia",
        "malaysia",
        "singapore",
        "philippines",
    ]:
        return "Asian"
    if c in ["india", "pakistan", "bangladesh", "sri lanka", "nepal", "afghanistan"]:
        return "South Asian"
    if c in [
        "egypt",
        "morocco",
        "algeria",
        "tunisia",
        "libya",
        "sudan",
        "saudi arabia",
        "united arab emirates",
        "qatar",
        "kuwait",
        "oman",
        "bahrain",
        "jordan",
        "lebanon",
        "israel",
        "iraq",
        "iran",
        "syria",
        "yemen",
    ]:
        return "Middle Eastern"
    if c in [
        "nigeria",
        "kenya",
        "ethiopia",
        "ghana",
        "senegal",
        "rwanda",
        "uganda",
        "tanzania",
        "mozambique",
        "zimbabwe",
        "zambia",
        "south africa",
        "namibia",
        "botswana",
        "madagascar",
        "cameroon",
        "civ",
        "mali",
    ]:
        return "Black"
    if c in [
        "mexico",
        "cuba",
        "panama",
        "colombia",
        "peru",
        "ecuador",
        "brazil",
        "argentina",
        "chile",
        "uruguay",
        "venezuela",
        "bolivia",
        "paraguay",
    ]:
        return "Latino"
    if c in ["fiji", "papua new guinea", "samoa", "tonga"]:
        return "Pacific Islander"
    if c in [
        "united kingdom",
        "ireland",
        "france",
        "germany",
        "spain",
        "portugal",
        "italy",
        "greece",
        "poland",
        "czechia",
        "austria",
        "hungary",
        "netherlands",
        "belgium",
        "denmark",
        "sweden",
        "norway",
        "finland",
        "iceland",
        "russia",
        "ukraine",
        "belarus",
        "romania",
        "bulgaria",
    ]:
        return "White"
    if c in ["united states", "canada", "australia", "new zealand"]:
        return random.choice(["White", "White", "Black", "Asian", "Latino", "Mixed"])
    return "Mixed"


_fakers: dict[str, Faker] = {}


def get_faker(country: str, region: str) -> Faker:
    locale = COUNTRY_TO_LOCALE.get(country)
    if not locale:
        locale = REGION_FALLBACK.get(region, "en_US")

    if locale not in _fakers:
        try:
            _fakers[locale] = Faker(locale)
        except Exception:
            _fakers[locale] = Faker("en_US")

    return _fakers[locale]


def build_profile_pool(
    cities: list[dict[str, Any]], count: int = 1200
) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for _ in range(count):
        city = random.choice(cities)
        country = city.get("country", "")
        region = city.get("region", "North America")

        faker = get_faker(country, region)
        is_working = random.random() > 0.35

        profiles.append(
            {
                "name": faker.name(),
                "age": random.randint(18, 64),
                "race": get_ethnicity(country),
                "roleLabel": "Job" if is_working else "Schooling",
                "roleValue": random.choice(CAREERS if is_working else SCHOOLS),
            }
        )
    return profiles

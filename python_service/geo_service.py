"""
geo_service.py - Authoritative Country, State & Territory Geographic Resolution Engine.
Loads global country and state database from CSV files to enhance shipping address
parsing, state code resolution (e.g. TX -> Texas, KA -> Karnataka, ON -> Ontario, NSW -> New South Wales),
and country standardization.
"""

import os
import csv
import re
from typing import Optional, Dict, Tuple, List, Any
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
COUNTRIES_CSV = os.path.join(DATA_DIR, "countries.csv")
STATES_CSV = os.path.join(DATA_DIR, "states.csv")

# Lookup tables initialized once
COUNTRIES_BY_ISO2: Dict[str, Dict[str, Any]] = {}
COUNTRIES_BY_ISO3: Dict[str, Dict[str, Any]] = {}
COUNTRIES_BY_NAME: Dict[str, Dict[str, Any]] = {}
STATES_BY_COUNTRY_AND_CODE: Dict[Tuple[str, str], str] = {}
STATES_BY_NAME: Dict[str, Dict[str, str]] = {}
ALL_STATE_CODES: Dict[str, List[Dict[str, str]]] = {}


def _init_geo_data():
    global COUNTRIES_BY_ISO2, COUNTRIES_BY_ISO3, COUNTRIES_BY_NAME
    global STATES_BY_COUNTRY_AND_CODE, STATES_BY_NAME, ALL_STATE_CODES

    if COUNTRIES_BY_ISO2:
        return

    # 1. Load Countries
    if os.path.exists(COUNTRIES_CSV):
        try:
            with open(COUNTRIES_CSV, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = (row.get("name") or "").strip()
                    iso2 = (row.get("iso2") or "").strip().upper()
                    iso3 = (row.get("iso3") or "").strip().upper()
                    if not name:
                        continue
                    c_info = {
                        "name": name,
                        "iso2": iso2,
                        "iso3": iso3,
                        "currency": row.get("currency", ""),
                        "phone_code": row.get("phone_code", "")
                    }
                    if iso2:
                        COUNTRIES_BY_ISO2[iso2] = c_info
                    if iso3:
                        COUNTRIES_BY_ISO3[iso3] = c_info
                    COUNTRIES_BY_NAME[name.lower()] = c_info
        except Exception:
            pass

    # Built-in fallback countries if CSV is missing or empty
    if not COUNTRIES_BY_ISO2:
        defaults = [
            ("United States", "US", "USA"),
            ("India", "IN", "IND"),
            ("Canada", "CA", "CAN"),
            ("United Kingdom", "GB", "GBR"),
            ("Australia", "AU", "AUS"),
            ("Germany", "DE", "DEU"),
            ("France", "FR", "FRA"),
            ("China", "CN", "CHN"),
            ("Japan", "JP", "JPN"),
            ("United Arab Emirates", "AE", "ARE")
        ]
        for name, i2, i3 in defaults:
            info = {"name": name, "iso2": i2, "iso3": i3}
            COUNTRIES_BY_ISO2[i2] = info
            COUNTRIES_BY_ISO3[i3] = info
            COUNTRIES_BY_NAME[name.lower()] = info

    # 2. Load States / Provinces
    if os.path.exists(STATES_CSV):
        try:
            with open(STATES_CSV, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    st_name = (row.get("name") or "").strip()
                    c_code = (row.get("country_code") or "").strip().upper()
                    st_code = (row.get("state_code") or "").strip().upper()
                    if not st_name or not c_code:
                        continue
                    
                    c_info = COUNTRIES_BY_ISO2.get(c_code, {})
                    c_name = c_info.get("name", c_code)

                    if st_code:
                        STATES_BY_COUNTRY_AND_CODE[(c_code, st_code)] = st_name
                        if st_code not in ALL_STATE_CODES:
                            ALL_STATE_CODES[st_code] = []
                        ALL_STATE_CODES[st_code].append({
                            "state_name": st_name,
                            "country_name": c_name,
                            "country_code": c_code,
                            "state_code": st_code
                        })

                    STATES_BY_NAME[st_name.lower()] = {
                        "state_name": st_name,
                        "country_name": c_name,
                        "country_code": c_code,
                        "state_code": st_code
                    }
        except Exception:
            pass


# Ensure data is initialized
_init_geo_data()


def resolve_country(text: str) -> Optional[Dict[str, str]]:
    """Resolves a raw text token or address snippet to canonical country metadata."""
    if not text:
        return None
    _init_geo_data()
    t_clean = text.strip()
    t_upper = t_clean.upper()
    t_lower = t_clean.lower()

    # Direct ISO match
    if len(t_upper) == 2 and t_upper in COUNTRIES_BY_ISO2:
        return COUNTRIES_BY_ISO2[t_upper]
    if len(t_upper) == 3 and t_upper in COUNTRIES_BY_ISO3:
        return COUNTRIES_BY_ISO3[t_upper]

    # Name match
    if t_lower in COUNTRIES_BY_NAME:
        return COUNTRIES_BY_NAME[t_lower]

    # Common aliases
    aliases = {
        "usa": "United States",
        "u.s.a.": "United States",
        "u.s.": "United States",
        "united states of america": "United States",
        "uk": "United Kingdom",
        "u.k.": "United Kingdom",
        "bharat": "India",
        "uae": "United Arab Emirates",
        "u.a.e.": "United Arab Emirates"
    }
    if t_lower in aliases:
        canonical = aliases[t_lower]
        return COUNTRIES_BY_NAME.get(canonical.lower())

    return None


def resolve_state(
    state_candidate: str,
    country_hint: Optional[str] = None
) -> Optional[Dict[str, str]]:
    """
    Resolves state abbreviation or full name to canonical state and country.
    E.g.
    resolve_state("TX", "US") -> {"state_name": "Texas", "country_name": "United States", "country_code": "US", "state_code": "TX"}
    resolve_state("Karnataka", None) -> {"state_name": "Karnataka", "country_name": "India", "country_code": "IN", "state_code": "KA"}
    """
    if not state_candidate:
        return None
    _init_geo_data()
    st_clean = state_candidate.strip()
    st_upper = st_clean.upper()
    st_lower = st_clean.lower()

    # Determine country ISO2 if provided
    c_iso2 = None
    if country_hint:
        c_obj = resolve_country(country_hint)
        if c_obj:
            c_iso2 = c_obj.get("iso2")

    # 1. Try (Country, StateCode) lookup
    if c_iso2 and (c_iso2, st_upper) in STATES_BY_COUNTRY_AND_CODE:
        full_name = STATES_BY_COUNTRY_AND_CODE[(c_iso2, st_upper)]
        c_name = COUNTRIES_BY_ISO2.get(c_iso2, {}).get("name", c_iso2)
        return {
            "state_name": full_name,
            "country_name": c_name,
            "country_code": c_iso2,
            "state_code": st_upper
        }

    # 2. Try State Name lookup
    if st_lower in STATES_BY_NAME:
        return STATES_BY_NAME[st_lower]

    # 3. Try global state code if unique or prioritizing major shipping hubs (US, IN, CA, AU)
    if st_upper in ALL_STATE_CODES:
        candidates = ALL_STATE_CODES[st_upper]
        if c_iso2:
            for cand in candidates:
                if cand["country_code"] == c_iso2:
                    return cand
        # Prioritize major shipping regions if no country hint
        priority_countries = ["US", "IN", "CA", "AU", "GB", "DE"]
        for p_code in priority_countries:
            for cand in candidates:
                if cand["country_code"] == p_code:
                    return cand
        return candidates[0]

    return None

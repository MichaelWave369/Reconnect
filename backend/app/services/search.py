from __future__ import annotations

import hashlib
import json
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from ..db import db_cursor

DEFAULT_CACHE_DAYS = int(__import__("os").getenv("RECONNECT_CACHE_DAYS", "7"))


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _url(s: str) -> str:
    return urllib.parse.quote(s or "")


def _gsite(query_str: str, site: str) -> str:
    return f"https://www.google.com/search?q={urllib.parse.quote(query_str + ' site:' + site)}"


def _gsearch(query_str: str) -> str:
    return f"https://www.google.com/search?q={urllib.parse.quote(query_str)}"


def normalize_query(q: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "full_name",
        "dob",
        "aliases",
        "last_known_locations",
        "location",
        "relatives",
        "local_only",
    ]
    out: Dict[str, Any] = {}
    for k in keys:
        v = q.get(k)
        if isinstance(v, str):
            v = v.strip()
        out[k] = v
    return out


def query_hash(q: Dict[str, Any]) -> str:
    normalized = normalize_query(q)
    payload = json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ─── Source Categories ───────────────────────────────────────────────────────
# Each source has: source, category, url (built dynamically), notes, priority (1=essential, 2=important, 3=supplementary),
# and guidance (what to do if you find something)


def build_linkouts(q: Dict[str, Any]) -> List[Dict[str, Any]]:
    name = (q.get("full_name") or "").strip()
    dob = (q.get("dob") or "").strip()
    year = dob[:4] if len(dob) >= 4 else ""
    last = (q.get("last_known_locations") or q.get("location") or "").strip()
    state = _extract_state(last)
    relatives = (q.get("relatives") or "").strip()

    parts = [p for p in [name, year, last] if p]
    query_str = " ".join(parts)
    name_query = " ".join([p for p in [name, year] if p])

    linkouts: List[Dict[str, Any]] = []

    # ═══ CATEGORY 1: DEATH RECORDS & INDEXES ═══
    linkouts.extend(
        [
            {
                "source": "Social Security Death Index (SSDI)",
                "category": "death_records",
                "priority": 1,
                "url": f"https://www.familysearch.org/search/collection/1202535?q.givenName={_url(name.split()[0] if name else '')}&q.surname={_url(name.split()[-1] if name else '')}",
                "notes": "The gold standard for confirming U.S. deaths. Covers most deaths reported to SSA since 1962. If listed here, the person has died.",
                "guidance": "If found: note the death date and last residence ZIP. You can then request a death certificate from that state's vital records office.",
            },
            {
                "source": "FamilySearch (Free)",
                "category": "death_records",
                "priority": 1,
                "url": _gsite(query_str, "familysearch.org"),
                "notes": "Massive free genealogy portal. Search death indexes, vital records, census data, and linked family trees.",
                "guidance": "If found in death index: cross-reference with SSDI. If found in census/tree: follow family connections to find more recent records.",
            },
            {
                "source": "Find a Grave",
                "category": "death_records",
                "priority": 1,
                "url": f"https://www.findagrave.com/memorial/search?firstname={_url(name.split()[0] if name else '')}&lastname={_url(name.split()[-1] if name else '')}&birthyear={_url(year)}",
                "notes": "Community-submitted memorials with photos, burial locations, and often linked obituaries.",
                "guidance": "If found: note the cemetery and dates. Contact the cemetery for official records. Check linked family members on the memorial page.",
            },
            {
                "source": "BillionGraves",
                "category": "death_records",
                "priority": 2,
                "url": _gsite(query_str, "billiongraves.com"),
                "notes": "GPS-tagged headstone photos. Complements Find a Grave with different coverage.",
                "guidance": "If found: cross-reference with Find a Grave. The GPS coordinates can help you visit the exact location.",
            },
            {
                "source": "National Gravesite Locator (Veterans)",
                "category": "death_records",
                "priority": 2,
                "url": "https://gravelocator.cem.va.gov/",
                "notes": "If the person or their spouse served in the military, this can confirm burial in a VA or national cemetery.",
                "guidance": "If found: the VA can provide burial details. If the person was a veteran, additional benefits records may be available.",
            },
            {
                "source": "Ancestry Death & Burial Collection",
                "category": "death_records",
                "priority": 2,
                "url": _gsite(name_query + " death", "ancestry.com"),
                "notes": "Large collection of death certificates, burial records, and obituary indexes. Some results visible without subscription.",
                "guidance": "If found in search preview: note enough details to request official records from the relevant jurisdiction.",
            },
        ]
    )

    # ═══ CATEGORY 2: OBITUARIES ═══
    linkouts.extend(
        [
            {
                "source": "Legacy.com",
                "category": "obituaries",
                "priority": 1,
                "url": _gsite(query_str, "legacy.com"),
                "notes": "The largest obituary aggregator in the U.S. Covers major and regional newspapers.",
                "guidance": "If found: the obituary often lists surviving family, funeral home, and burial location — all useful for official records requests.",
            },
            {
                "source": "Newspapers.com",
                "category": "obituaries",
                "priority": 2,
                "url": _gsite(query_str + " obituary", "newspapers.com"),
                "notes": "Vast archive of digitized newspapers. Free previews; full access via subscription or many public libraries.",
                "guidance": "If found: note the newspaper name and date. Your local library may have free access to the full text.",
            },
            {
                "source": "Tributes.com",
                "category": "obituaries",
                "priority": 3,
                "url": _gsite(query_str, "tributes.com"),
                "notes": "Obituary and memorial aggregator with wide funeral home coverage.",
                "guidance": "If found: contact the listed funeral home — they often have burial records and can confirm details.",
            },
            {
                "source": "Echovita",
                "category": "obituaries",
                "priority": 3,
                "url": _gsite(query_str, "echovita.com"),
                "notes": "Aggregates obituaries from funeral homes across the U.S.",
                "guidance": "Cross-reference any findings with Legacy.com or the newspaper of record.",
            },
            {
                "source": "Google Obituary Search",
                "category": "obituaries",
                "priority": 2,
                "url": _gsearch(f'"{name}" obituary {last} {year}'),
                "notes": "Direct Google search with the name in quotes. Sometimes catches obituaries not indexed by aggregators.",
                "guidance": "If found: save the URL and add it as evidence. Note the source for reliability assessment.",
            },
        ]
    )

    # ═══ CATEGORY 3: OFFICIAL / GOVERNMENT RECORDS ═══
    linkouts.extend(
        [
            {
                "source": "State Vital Records Directory (CDC)",
                "category": "official_records",
                "priority": 1,
                "url": "https://www.cdc.gov/nchs/w2w/index.htm",
                "notes": "Official directory for where to request birth, death, and marriage certificates in every U.S. state and territory.",
                "guidance": "Use this to find the exact office, form, fee, and process for the state where the person was last known.",
            },
            {
                "source": "County Court Records (Judyrecords)",
                "category": "official_records",
                "priority": 2,
                "url": f"https://www.judyrecords.com/search?t=name&q={_url(name)}",
                "notes": "Free search of court records across most U.S. counties. Covers civil, criminal, bankruptcy, probate.",
                "guidance": "If found: probate records can indicate death. Civil records can show recent activity (meaning the person was alive at filing).",
            },
            {
                "source": "Federal Bureau of Prisons Inmate Locator",
                "category": "official_records",
                "priority": 2,
                "url": f"https://www.bop.gov/inmateloc/",
                "notes": "Searchable database of current and former federal inmates. If someone 'disappeared,' this is worth checking.",
                "guidance": "If found: note the facility and release date. The BOP can provide additional details to immediate family.",
            },
            {
                "source": "State Prison/DOC Inmate Search",
                "category": "official_records",
                "priority": 2,
                "url": _gsearch(f"{name} inmate {state or ''} department of corrections"),
                "notes": "Most states have online inmate locators. Search the state DOC directly for the most current information.",
                "guidance": "If found: note the facility and status. Many DOCs allow family to request visitation or contact information.",
            },
            {
                "source": "PACER (Federal Courts)",
                "category": "official_records",
                "priority": 3,
                "url": "https://pacer.uscourts.gov/",
                "notes": "Federal court records including bankruptcy, civil, and criminal cases. Small per-page fee.",
                "guidance": "If found: bankruptcy filings require a current address. This can be a strong lead.",
            },
            {
                "source": "VINELink (Victim Notification)",
                "category": "official_records",
                "priority": 3,
                "url": f"https://www.vinelink.com/#/search",
                "notes": "Nationwide offender search. Can confirm if someone is or was in county or state custody.",
                "guidance": "If found: note the custody status and location. This confirms the person is alive as of the custody date.",
            },
        ]
    )

    # ═══ CATEGORY 4: PEOPLE SEARCH / PUBLIC RECORDS ═══
    linkouts.extend(
        [
            {
                "source": "TruePeopleSearch",
                "category": "people_search",
                "priority": 1,
                "url": f"https://www.truepeoplesearch.com/results?name={_url(name)}&citystatezip={_url(last)}",
                "notes": "Free people search with addresses, phone numbers, relatives, and associates. One of the most comprehensive free options.",
                "guidance": "If found with a recent address: that's a strong indicator the person is alive. Note the address and any listed relatives.",
            },
            {
                "source": "FastPeopleSearch",
                "category": "people_search",
                "priority": 2,
                "url": f"https://www.fastpeoplesearch.com/name/{_url(name.replace(' ', '-') if name else '')}",
                "notes": "Similar to TruePeopleSearch. Cross-reference results between both for confirmation.",
                "guidance": "If the person shows a current address, they are likely alive. If the listing shows 'deceased,' follow up with official records.",
            },
            {
                "source": "That's Them",
                "category": "people_search",
                "priority": 3,
                "url": f"https://thatsthem.com/name/{_url(name.replace(' ', '-') if name else '')}",
                "notes": "Free people lookup with address history, phone, email, and IP data.",
                "guidance": "Useful for establishing a timeline of where the person has lived.",
            },
            {
                "source": "WhitePages",
                "category": "people_search",
                "priority": 2,
                "url": f"https://www.whitepages.com/name/{_url(name.replace(' ', '-') if name else '')}/{_url(last.split(',')[0].strip() if last else '')}",
                "notes": "Classic directory. Free basic results; premium for full reports.",
                "guidance": "If listed: note the address and cross-reference with other sources. If not listed, the person may have moved or passed.",
            },
        ]
    )

    # ═══ CATEGORY 5: MISSING PERSONS DATABASES ═══
    linkouts.extend(
        [
            {
                "source": "NamUs (National Missing & Unidentified Persons)",
                "category": "missing_persons",
                "priority": 1,
                "url": "https://namus.nij.ojp.gov/",
                "notes": "The federal clearinghouse for missing and unidentified persons. Free, searchable, and authoritative.",
                "guidance": "If found in the missing persons database: contact NamUs directly. If found in the unidentified remains database, this may provide closure. NamUs has case managers who can help.",
            },
            {
                "source": "NCIC Missing Persons (via NamUs)",
                "category": "missing_persons",
                "priority": 2,
                "url": _gsearch(f'"{name}" missing person {state or ""}'),
                "notes": "The FBI's National Crime Information Center database is not publicly searchable, but local law enforcement can query it. NamUs feeds into NCIC.",
                "guidance": "If you believe the person may be officially missing, file a report with local police. They can query NCIC.",
            },
            {
                "source": "The Charley Project",
                "category": "missing_persons",
                "priority": 2,
                "url": _gsite(name_query, "charleyproject.org"),
                "notes": "Detailed case profiles for cold missing persons cases in the U.S.",
                "guidance": "If found: the profile will have investigating agency contact information.",
            },
            {
                "source": "The Doe Network",
                "category": "missing_persons",
                "priority": 3,
                "url": _gsite(name_query, "doenetwork.org"),
                "notes": "Volunteer organization cataloging unidentified persons and missing persons. International coverage.",
                "guidance": "If a match seems possible: contact both the Doe Network and the relevant law enforcement agency.",
            },
        ]
    )

    # ═══ CATEGORY 6: UNCLAIMED PROPERTY / ASSETS ═══
    linkouts.extend(
        [
            {
                "source": "MissingMoney.com (NAUPA)",
                "category": "unclaimed_assets",
                "priority": 1,
                "url": f"https://www.missingmoney.com/en/Property/SearchIndex",
                "notes": "National portal for unclaimed property from all 50 states. People are often 'found' through unclaimed assets — bank accounts, insurance, tax refunds.",
                "guidance": "If found: the state holding the property can tell you the last known address on file. This is a surprisingly effective way to trace someone.",
            },
            {
                "source": "Unclaimed.org (State Treasurers)",
                "category": "unclaimed_assets",
                "priority": 2,
                "url": "https://unclaimed.org/",
                "notes": "Official directory linking to each state's unclaimed property search.",
                "guidance": "Search both the state where the person was last known AND their birth state.",
            },
            {
                "source": "U.S. Treasury Unclaimed Assets",
                "category": "unclaimed_assets",
                "priority": 3,
                "url": "https://www.treasurydirect.gov/indiv/tools/tools_treasuryhunt.htm",
                "notes": "Search for unclaimed U.S. savings bonds. Older individuals may have forgotten bonds from decades ago.",
                "guidance": "If found: this confirms identity and can be claimed by heirs with proper documentation.",
            },
            {
                "source": "PBGC Unclaimed Pensions",
                "category": "unclaimed_assets",
                "priority": 3,
                "url": "https://search.pbgc.gov/mp/",
                "notes": "Search for unclaimed pensions from companies that went through PBGC. Many older workers have unclaimed retirement benefits.",
                "guidance": "If found: PBGC can provide the last known address on file and the pension can be claimed by the person or their estate.",
            },
            {
                "source": "Life Insurance Policy Locator (NAIC)",
                "category": "unclaimed_assets",
                "priority": 2,
                "url": "https://eapps.naic.org/life-policy-locator/",
                "notes": "Free service to search for lost life insurance policies or annuities. Takes 90 days for results to come back by mail.",
                "guidance": "Submit a request. If a policy is found, the insurer will contact you. This can confirm both identity and death (if a death benefit was paid).",
            },
        ]
    )

    # ═══ CATEGORY 7: SOCIAL MEDIA & ONLINE PRESENCE ═══
    linkouts.extend(
        [
            {
                "source": "Facebook People Search",
                "category": "social_media",
                "priority": 1,
                "url": f"https://www.facebook.com/search/people/?q={_url(name)}",
                "notes": "Many people, even older adults, have Facebook profiles. Memorialized profiles indicate the person has passed.",
                "guidance": "If found active: the profile may show recent activity, location, friends. If memorialized (candle icon): the person has passed and someone reported it to Facebook.",
            },
            {
                "source": "LinkedIn",
                "category": "social_media",
                "priority": 3,
                "url": _gsearch(f'site:linkedin.com "{name}" {last}'),
                "notes": "Professional profiles. Less useful for older or retired individuals, but can show employment history.",
                "guidance": "If found with recent activity, the person is likely alive. Note any listed employers or locations.",
            },
            {
                "source": "Pipl / Social Media Search",
                "category": "social_media",
                "priority": 3,
                "url": _gsearch(
                    f'"{name}" {last} site:facebook.com OR site:linkedin.com OR site:twitter.com'
                ),
                "notes": "Broad social media search across multiple platforms.",
                "guidance": "Any social media activity with timestamps can help establish a timeline of when the person was last active online.",
            },
        ]
    )

    # ═══ CATEGORY 8: GENEALOGY / FAMILY CONNECTIONS ═══
    linkouts.extend(
        [
            {
                "source": "Ancestry Family Trees",
                "category": "genealogy",
                "priority": 2,
                "url": _gsite(name_query, "ancestry.com"),
                "notes": "Public family trees may include the person or their relatives. Can reveal family connections you didn't know about.",
                "guidance": "If found in a tree: contact the tree owner (they're likely a relative). They may have current information.",
            },
            {
                "source": "MyHeritage",
                "category": "genealogy",
                "priority": 3,
                "url": _gsite(name_query, "myheritage.com"),
                "notes": "Large genealogy platform with family trees, historical records, and DNA matching.",
                "guidance": "Similar to Ancestry — look for family tree connections and contact the owners.",
            },
            {
                "source": "GEDmatch (DNA Reunion)",
                "category": "genealogy",
                "priority": 2,
                "url": "https://www.gedmatch.com/",
                "notes": "If you have DNA test results, GEDmatch can match you with genetic relatives who may know the person's whereabouts.",
                "guidance": "Upload your DNA data (from Ancestry, 23andMe, etc.). Matches are ranked by relationship closeness. Reach out to close matches.",
            },
            {
                "source": "FindMyPast",
                "category": "genealogy",
                "priority": 3,
                "url": _gsite(name_query, "findmypast.com"),
                "notes": "Strong for UK/international records but also has U.S. coverage.",
                "guidance": "Useful if the person has international connections.",
            },
        ]
    )

    # ═══ CATEGORY 9: PROPERTY / ADDRESS RECORDS ═══
    linkouts.extend(
        [
            {
                "source": "County Property Records",
                "category": "property",
                "priority": 2,
                "url": _gsearch(f"{name} property records {state or last}"),
                "notes": "Most counties have online property search. Property ownership records are public and often have current mailing addresses.",
                "guidance": "If found: the property address and mailing address can confirm where the person lives or lived. Tax records show the last payment date.",
            },
            {
                "source": "Voter Registration Records",
                "category": "property",
                "priority": 2,
                "url": _gsearch(f"{name} voter registration {state or ''}"),
                "notes": "Voter registration is public in most states. Shows name, address, date of birth, and registration status.",
                "guidance": "If actively registered: the person was alive at the last registration update. If cancelled due to death: this confirms passing.",
            },
        ]
    )

    # ═══ CATEGORY 10: HOSPITAL / MEDICAL ═══
    linkouts.extend(
        [
            {
                "source": "Medicare.gov (Provider/Plan Search)",
                "category": "medical",
                "priority": 3,
                "url": "https://www.medicare.gov/",
                "notes": "While patient records are private, Medicare eligibility status can sometimes be checked. Social Security can confirm if benefits are active.",
                "guidance": "Call SSA at 1-800-772-1213. They cannot reveal an address, but may confirm if benefits are being collected (which means the person is alive).",
            },
        ]
    )

    # ═══ CATEGORY 11: NEWS / MEDIA ═══
    linkouts.extend(
        [
            {
                "source": "Google News Archive",
                "category": "news",
                "priority": 2,
                "url": f"https://news.google.com/search?q={_url(name + ' ' + last)}",
                "notes": "Search news articles mentioning the person. Can reveal accidents, arrests, public events, or community involvement.",
                "guidance": "If found in news: note the date and context. This can establish a timeline of activity.",
            },
        ]
    )

    # ═══ Add relationship-multiplied searches ═══
    if relatives:
        for rel_raw in relatives.split(","):
            rel = rel_raw.strip()
            if not rel or len(rel) < 3:
                continue
            # Add targeted searches for each known relative
            linkouts.append(
                {
                    "source": f"Relative Search: {rel}",
                    "category": "relationship_search",
                    "priority": 2,
                    "url": _gsearch(f'"{rel}" "{name}" {last}'),
                    "notes": f"Search for {rel} alongside {name}. Relatives often appear in shared records — obituaries, property, court documents.",
                    "guidance": f"If found together: this confirms the connection and may reveal current information about either person.",
                }
            )
            linkouts.append(
                {
                    "source": f"Obituary Cross-Reference: {rel}",
                    "category": "relationship_search",
                    "priority": 2,
                    "url": _gsearch(f'"{rel}" obituary {last}'),
                    "notes": f"Search for {rel}'s obituary. Obituaries of relatives often mention the person you're looking for, even if their own obituary doesn't exist online.",
                    "guidance": f"If {rel}'s obituary lists {name} as 'preceded in death by': this confirms {name} passed before {rel}. If listed as surviving: {name} was alive at that date.",
                }
            )

    # ═══ Add alias-based searches ═══
    aliases_str = (q.get("aliases") or "").strip()
    if aliases_str:
        for alias_raw in aliases_str.split(","):
            alias = alias_raw.strip()
            if not alias or len(alias) < 2 or alias.lower() == name.lower():
                continue
            alias_parts = [p for p in [alias, year, last] if p]
            alias_query = " ".join(alias_parts)
            linkouts.append(
                {
                    "source": f"Alias Search: {alias}",
                    "category": "people_search",
                    "priority": 1,
                    "url": _gsearch(f'"{alias}" {last} {year}'),
                    "notes": f"Search for the alternate name '{alias}'. Records may be filed under maiden names, married names, or nicknames.",
                    "guidance": f"If found under '{alias}': this may be the same person under a different name. Cross-reference dates and locations to confirm.",
                }
            )
            linkouts.append(
                {
                    "source": f"Alias Death Search: {alias}",
                    "category": "death_records",
                    "priority": 2,
                    "url": _gsite(alias_query, "familysearch.org"),
                    "notes": f"Search death indexes for '{alias}' — records may be filed under this name instead of '{name}'.",
                    "guidance": f"Death records sometimes use maiden names or legal name variants. Check dates and locations carefully.",
                }
            )

    return linkouts


def _extract_state(location: str) -> str:
    """Try to extract a U.S. state abbreviation or name from a location string."""
    if not location:
        return ""
    STATE_ABBREVS = {
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
        "DC",
    }
    parts = [p.strip().upper() for p in location.replace(";", ",").split(",")]
    for p in reversed(parts):
        token = p.strip().split()[-1] if p.strip().split() else ""
        if token in STATE_ABBREVS:
            return token
    return ""


def get_cached(qh: str) -> Tuple[bool, Dict[str, Any] | None]:
    now = _now_iso()
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT results_json, created_at, expires_at FROM search_cache WHERE query_hash=?",
            (qh,),
        ).fetchone()
        if not row:
            return False, None
        if row["expires_at"] <= now:
            cur.execute("DELETE FROM search_cache WHERE query_hash=?", (qh,))
            return False, None
        return True, {
            "results": json.loads(row["results_json"]),
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
        }


def set_cache(qh: str, q: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, str]:
    created_at = _now_iso()
    expires_at = (datetime.utcnow() + timedelta(days=DEFAULT_CACHE_DAYS)).replace(
        microsecond=0
    ).isoformat() + "Z"
    with db_cursor() as cur:
        cur.execute(
            "INSERT OR REPLACE INTO search_cache(query_hash, query_json, results_json, created_at, expires_at) VALUES(?,?,?,?,?)",
            (
                qh,
                json.dumps(normalize_query(q), ensure_ascii=False, sort_keys=True),
                json.dumps(results, ensure_ascii=False, sort_keys=True),
                created_at,
                expires_at,
            ),
        )
    return {"created_at": created_at, "expires_at": expires_at}


def run_linkout_search(q: Dict[str, Any]) -> Dict[str, Any]:
    qh = query_hash(q)
    cached, payload = get_cached(qh)
    if cached and payload:
        return {
            "status": "cached",
            "cached": True,
            "query_hash": qh,
            "results": payload["results"],
            "created_at": payload["created_at"],
        }

    results = build_linkouts(q)
    cache_meta = set_cache(qh, q, results)
    return {
        "status": "linkouts",
        "cached": False,
        "query_hash": qh,
        "results": results,
        "created_at": cache_meta["created_at"],
    }

"""
State-specific vital records routing.
Maps each U.S. state to its vital records office, contact info, fees, and request process.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


# ─── State Vital Records Database ──────────────────────────────────────────
# Each entry: office, url, phone, death_cert_fee, processing_time, notes, online_available

STATE_VITAL_RECORDS: Dict[str, Dict[str, Any]] = {
    "AL": {"state": "Alabama", "office": "Center for Health Statistics", "url": "https://www.alabamapublichealth.gov/vitalrecords/", "phone": "(334) 206-5418", "death_cert_fee": "$15", "processing": "4-6 weeks by mail", "online": True, "notes": "Online ordering available through VitalChek. Records from 1908-present."},
    "AK": {"state": "Alaska", "office": "Bureau of Vital Statistics", "url": "https://health.alaska.gov/dph/VitalStats/", "phone": "(907) 465-3391", "death_cert_fee": "$30", "processing": "4-8 weeks", "online": True, "notes": "Records from 1913-present. Expedited service available."},
    "AZ": {"state": "Arizona", "office": "Office of Vital Records", "url": "https://azdhs.gov/vital-records/", "phone": "(602) 364-1300", "death_cert_fee": "$20", "processing": "6-8 weeks by mail", "online": True, "notes": "Records from July 1909-present. County recorders may have earlier records."},
    "AR": {"state": "Arkansas", "office": "Vital Records", "url": "https://www.healthy.arkansas.gov/programs-services/topics/certificates-background-requests", "phone": "(501) 661-2336", "death_cert_fee": "$12", "processing": "4-6 weeks", "online": True, "notes": "Records from February 1914-present."},
    "CA": {"state": "California", "office": "Vital Records", "url": "https://www.cdph.ca.gov/Programs/CHSI/Pages/Vital-Records.aspx", "phone": "(916) 445-2684", "death_cert_fee": "$21", "processing": "10-14 weeks by mail", "online": True, "notes": "Records from July 1905-present. County registrars may be faster for recent deaths."},
    "CO": {"state": "Colorado", "office": "Vital Records", "url": "https://cdphe.colorado.gov/vitalrecords", "phone": "(303) 692-2200", "death_cert_fee": "$20", "processing": "4-6 weeks", "online": True, "notes": "Records from 1900-present."},
    "CT": {"state": "Connecticut", "office": "Vital Records", "url": "https://portal.ct.gov/DPH/Vital-Records/Vital-Records", "phone": "(860) 509-7700", "death_cert_fee": "$20", "processing": "4-6 weeks", "online": True, "notes": "Records from July 1897-present. Town clerks have records back to the 1600s."},
    "DE": {"state": "Delaware", "office": "Office of Vital Statistics", "url": "https://dhss.delaware.gov/dhss/dph/ss/vitalstats.html", "phone": "(302) 744-4549", "death_cert_fee": "$25", "processing": "4-8 weeks", "online": False, "notes": "Records from 1930-present. Earlier records at DE Public Archives."},
    "DC": {"state": "District of Columbia", "office": "Vital Records Division", "url": "https://dchealth.dc.gov/service/death-certificates", "phone": "(877) 572-6332", "death_cert_fee": "$18", "processing": "5-10 business days", "online": True, "notes": "Records from 1874-present. Walk-in service available."},
    "FL": {"state": "Florida", "office": "Bureau of Vital Statistics", "url": "http://www.floridahealth.gov/certificates/certificates/index.html", "phone": "(904) 359-6900", "death_cert_fee": "$5", "processing": "2-4 weeks", "online": True, "notes": "Records from 1877-present. Florida is one of the cheapest states for death certificates."},
    "GA": {"state": "Georgia", "office": "Vital Records", "url": "https://dph.georgia.gov/vital-records", "phone": "(404) 679-4702", "death_cert_fee": "$25", "processing": "4-6 weeks", "online": True, "notes": "Records from 1919-present. County probate courts have earlier records."},
    "HI": {"state": "Hawaii", "office": "Vital Records", "url": "https://health.hawaii.gov/vitalrecords/", "phone": "(808) 586-4533", "death_cert_fee": "$10", "processing": "4-6 weeks", "online": True, "notes": "Records from 1853-present."},
    "ID": {"state": "Idaho", "office": "Bureau of Vital Records and Health Statistics", "url": "https://healthandwelfare.idaho.gov/services-programs/health/vital-records-and-health-statistics", "phone": "(208) 334-5988", "death_cert_fee": "$16", "processing": "4-6 weeks", "online": True, "notes": "Records from July 1911-present."},
    "IL": {"state": "Illinois", "office": "Division of Vital Records", "url": "https://dph.illinois.gov/topics-services/birth-death-other-records/death-records.html", "phone": "(217) 782-6553", "death_cert_fee": "$19", "processing": "4-6 weeks", "online": True, "notes": "Records from January 1916-present. Cook County has separate records."},
    "IN": {"state": "Indiana", "office": "Vital Records", "url": "https://www.in.gov/health/vital-records/", "phone": "(317) 233-2700", "death_cert_fee": "$10", "processing": "4-6 weeks", "online": True, "notes": "Records from 1900-present."},
    "IA": {"state": "Iowa", "office": "Bureau of Health Statistics", "url": "https://idph.iowa.gov/health-statistics/vital-records", "phone": "(515) 281-4944", "death_cert_fee": "$20", "processing": "4-6 weeks", "online": True, "notes": "Records from July 1880-present."},
    "KS": {"state": "Kansas", "office": "Office of Vital Statistics", "url": "https://www.kdheks.gov/vital/", "phone": "(785) 296-1400", "death_cert_fee": "$15", "processing": "4-6 weeks", "online": True, "notes": "Records from July 1911-present."},
    "KY": {"state": "Kentucky", "office": "Vital Statistics", "url": "https://chfs.ky.gov/agencies/dph/dehp/vitalstatisticsb/Pages/default.aspx", "phone": "(502) 564-4212", "death_cert_fee": "$10", "processing": "4-6 weeks", "online": True, "notes": "Records from January 1911-present."},
    "LA": {"state": "Louisiana", "office": "Vital Records Registry", "url": "https://ldh.la.gov/page/vital-records-services", "phone": "(504) 593-5100", "death_cert_fee": "$15", "processing": "4-6 weeks", "online": True, "notes": "Records from 1914-present. Parish clerk has earlier records."},
    "ME": {"state": "Maine", "office": "Office of Vital Records", "url": "https://www.maine.gov/dhhs/mecdc/public-health-systems/data-research/vital-records/", "phone": "(207) 287-3181", "death_cert_fee": "$15", "processing": "4-6 weeks", "online": True, "notes": "Records from 1892-present. Town clerks have earlier records."},
    "MD": {"state": "Maryland", "office": "Division of Vital Records", "url": "https://health.maryland.gov/vsa/Pages/Home.aspx", "phone": "(410) 764-3038", "death_cert_fee": "$24", "processing": "4-6 weeks", "online": True, "notes": "Records from August 1898-present."},
    "MA": {"state": "Massachusetts", "office": "Registry of Vital Records and Statistics", "url": "https://www.mass.gov/orgs/registry-of-vital-records-and-statistics", "phone": "(617) 740-2600", "death_cert_fee": "$20", "processing": "4-8 weeks", "online": True, "notes": "Records from 1841-present. Town/city clerk has earlier records."},
    "MI": {"state": "Michigan", "office": "Vital Records", "url": "https://www.michigan.gov/mdhhs/keep-mi-healthy/vitalrecords", "phone": "(517) 335-8666", "death_cert_fee": "$34", "processing": "8-10 weeks", "online": True, "notes": "Records from 1867-present. One of the more expensive states."},
    "MN": {"state": "Minnesota", "office": "Office of Vital Records", "url": "https://www.health.state.mn.us/people/vitalrecords/index.html", "phone": "(651) 201-5970", "death_cert_fee": "$13", "processing": "2-4 weeks", "online": True, "notes": "Records from January 1908-present."},
    "MS": {"state": "Mississippi", "office": "Vital Records", "url": "https://msdh.ms.gov/page/30,0,109.html", "phone": "(601) 206-8200", "death_cert_fee": "$15", "processing": "4-6 weeks", "online": True, "notes": "Records from November 1912-present."},
    "MO": {"state": "Missouri", "office": "Bureau of Vital Records", "url": "https://health.mo.gov/data/vitalrecords/", "phone": "(573) 751-6387", "death_cert_fee": "$14", "processing": "4-6 weeks", "online": True, "notes": "Records from January 1910-present."},
    "MT": {"state": "Montana", "office": "Office of Vital Statistics", "url": "https://dphhs.mt.gov/vitalrecords", "phone": "(406) 444-4228", "death_cert_fee": "$14", "processing": "4-8 weeks", "online": True, "notes": "Records from 1907-present."},
    "NE": {"state": "Nebraska", "office": "Vital Records", "url": "https://dhhs.ne.gov/Pages/vital-records.aspx", "phone": "(402) 471-2871", "death_cert_fee": "$16", "processing": "4-6 weeks", "online": True, "notes": "Records from 1904-present."},
    "NV": {"state": "Nevada", "office": "Office of Vital Records", "url": "https://dpbh.nv.gov/Programs/OR/Office_of_Vital_Records_-_Home/", "phone": "(775) 684-4242", "death_cert_fee": "$20", "processing": "6-8 weeks", "online": True, "notes": "Records from July 1911-present. County recorders have some earlier records."},
    "NH": {"state": "New Hampshire", "office": "Division of Vital Records Administration", "url": "https://www.dhhs.nh.gov/programs-services/vital-records", "phone": "(603) 271-4650", "death_cert_fee": "$15", "processing": "4-6 weeks", "online": True, "notes": "Records from 1640-present (one of the oldest collections in the U.S.)."},
    "NJ": {"state": "New Jersey", "office": "Office of Vital Statistics and Registration", "url": "https://www.state.nj.us/health/vital/", "phone": "(609) 292-4087", "death_cert_fee": "$25", "processing": "8-12 weeks", "online": True, "notes": "Records from June 1878-present. Can be slow — plan ahead."},
    "NM": {"state": "New Mexico", "office": "Bureau of Vital Records and Health Statistics", "url": "https://www.nmhealth.org/about/erd/bvrhs/vrr/", "phone": "(505) 827-0121", "death_cert_fee": "$10", "processing": "4-6 weeks", "online": True, "notes": "Records from 1899-present."},
    "NY": {"state": "New York", "office": "Vital Records Section", "url": "https://www.health.ny.gov/vital_records/", "phone": "(518) 474-3075", "death_cert_fee": "$30", "processing": "6-12 weeks", "online": True, "notes": "Records from 1880-present. NYC has a separate Vital Records office. Manhattan, Brooklyn, Bronx, Queens, Staten Island: nyc.gov/vitalrecords."},
    "NC": {"state": "North Carolina", "office": "Vital Records", "url": "https://vitalrecords.nc.gov/", "phone": "(919) 733-3526", "death_cert_fee": "$24", "processing": "4-6 weeks", "online": True, "notes": "Records from October 1913-present."},
    "ND": {"state": "North Dakota", "office": "Division of Vital Records", "url": "https://www.hhs.nd.gov/vital-records", "phone": "(701) 328-2360", "death_cert_fee": "$7", "processing": "2-4 weeks", "online": True, "notes": "Records from July 1893-present. Cheapest state for death certificates."},
    "OH": {"state": "Ohio", "office": "Bureau of Vital Statistics", "url": "https://odh.ohio.gov/know-our-programs/vital-statistics", "phone": "(614) 466-2531", "death_cert_fee": "$21.50", "processing": "4-6 weeks", "online": True, "notes": "Records from December 1908-present."},
    "OK": {"state": "Oklahoma", "office": "Vital Records", "url": "https://oklahoma.gov/health/vital-records.html", "phone": "(405) 271-4040", "death_cert_fee": "$15", "processing": "4-6 weeks", "online": True, "notes": "Records from October 1908-present."},
    "OR": {"state": "Oregon", "office": "Center for Health Statistics", "url": "https://www.oregon.gov/oha/PH/BIRTHDEATHCERTIFICATES/", "phone": "(971) 673-1190", "death_cert_fee": "$20", "processing": "4-6 weeks", "online": True, "notes": "Records from January 1903-present."},
    "PA": {"state": "Pennsylvania", "office": "Division of Vital Records", "url": "https://www.health.pa.gov/topics/certificates/Pages/Death-Certificates.aspx", "phone": "(724) 656-3100", "death_cert_fee": "$20", "processing": "6-8 weeks", "online": True, "notes": "Records from January 1906-present."},
    "RI": {"state": "Rhode Island", "office": "Office of Vital Records", "url": "https://health.ri.gov/records/", "phone": "(401) 222-2811", "death_cert_fee": "$20", "processing": "4-6 weeks", "online": True, "notes": "Records from 1853-present."},
    "SC": {"state": "South Carolina", "office": "Vital Records", "url": "https://scdhec.gov/vital-records", "phone": "(803) 898-3630", "death_cert_fee": "$12", "processing": "4-6 weeks", "online": True, "notes": "Records from January 1915-present."},
    "SD": {"state": "South Dakota", "office": "Vital Records", "url": "https://doh.sd.gov/records/", "phone": "(605) 773-4961", "death_cert_fee": "$15", "processing": "4-6 weeks", "online": True, "notes": "Records from July 1905-present."},
    "TN": {"state": "Tennessee", "office": "Office of Vital Records", "url": "https://www.tn.gov/health/health-program-areas/vital-records.html", "phone": "(615) 741-1763", "death_cert_fee": "$15", "processing": "4-6 weeks", "online": True, "notes": "Records from January 1914-present."},
    "TX": {"state": "Texas", "office": "Vital Statistics", "url": "https://www.dshs.texas.gov/vital-statistics", "phone": "(512) 776-7111", "death_cert_fee": "$20", "processing": "6-10 weeks", "online": True, "notes": "Records from 1903-present. County clerks may be faster for recent records."},
    "UT": {"state": "Utah", "office": "Office of Vital Records and Statistics", "url": "https://vitalrecords.utah.gov/", "phone": "(801) 538-6105", "death_cert_fee": "$20", "processing": "4-6 weeks", "online": True, "notes": "Records from 1905-present."},
    "VT": {"state": "Vermont", "office": "Vital Records", "url": "https://www.healthvermont.gov/stats/vital-records", "phone": "(802) 863-7275", "death_cert_fee": "$10", "processing": "4-6 weeks", "online": True, "notes": "Records from 1760-present (one of the oldest collections)."},
    "VA": {"state": "Virginia", "office": "Division of Vital Records", "url": "https://www.vdh.virginia.gov/vital-records/", "phone": "(804) 662-6200", "death_cert_fee": "$12", "processing": "4-6 weeks", "online": True, "notes": "Records from June 1912-present."},
    "WA": {"state": "Washington", "office": "Center for Health Statistics", "url": "https://doh.wa.gov/licenses-permits-and-certificates/vital-records", "phone": "(360) 236-4300", "death_cert_fee": "$20", "processing": "4-6 weeks", "online": True, "notes": "Records from July 1907-present."},
    "WV": {"state": "West Virginia", "office": "Vital Registration Office", "url": "https://dhhr.wv.gov/vitalreg/Pages/default.aspx", "phone": "(304) 558-2931", "death_cert_fee": "$12", "processing": "4-6 weeks", "online": True, "notes": "Records from January 1917-present."},
    "WI": {"state": "Wisconsin", "office": "Vital Records", "url": "https://www.dhs.wisconsin.gov/vital-records/index.htm", "phone": "(608) 266-1371", "death_cert_fee": "$20", "processing": "4-6 weeks", "online": True, "notes": "Records from October 1907-present."},
    "WY": {"state": "Wyoming", "office": "Vital Statistics Services", "url": "https://health.wyo.gov/admin/vitalstatistics/", "phone": "(307) 777-7591", "death_cert_fee": "$10", "processing": "4-6 weeks", "online": True, "notes": "Records from July 1909-present."},
}


def get_state_routing(state_abbrev: str) -> Optional[Dict[str, Any]]:
    """Get vital records routing for a specific state."""
    return STATE_VITAL_RECORDS.get(state_abbrev.upper())


def get_all_states() -> Dict[str, Dict[str, Any]]:
    """Return all state records."""
    return STATE_VITAL_RECORDS


def get_state_guidance(state_abbrev: str, subject_name: str = "") -> Dict[str, Any]:
    """Get comprehensive guidance for requesting records in a specific state."""
    info = get_state_routing(state_abbrev)
    if not info:
        return {"error": f"No information for state: {state_abbrev}"}

    steps = [
        f"1. Visit the {info['state']} vital records office online: {info['url']}",
        f"2. Download or fill out the death certificate request form.",
        f"3. You will need: the full name of the deceased, approximate date of death, your relationship to the deceased, and your photo ID.",
        f"4. Fee: {info['death_cert_fee']} per certified copy.",
        f"5. Processing time: approximately {info['processing']}.",
        f"6. Phone for questions: {info['phone']}.",
    ]

    if info.get("online"):
        steps.append("7. Online ordering may be available through VitalChek (faster but typically costs more).")

    tips = [
        "If you don't know the exact date of death, most offices can search a date range (e.g., 2015-2023).",
        "If the person died in a different state than where they lived, check BOTH states.",
        "County-level offices are sometimes faster than state offices for recent deaths.",
        "If you're told 'no record found,' this is actually informative — it suggests the person may not have died in that state.",
    ]

    return {
        "state": info["state"],
        "state_abbrev": state_abbrev.upper(),
        "office": info["office"],
        "url": info["url"],
        "phone": info["phone"],
        "fee": info["death_cert_fee"],
        "processing": info["processing"],
        "online_available": info.get("online", False),
        "coverage_notes": info.get("notes", ""),
        "steps": steps,
        "tips": tips,
    }

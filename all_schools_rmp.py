"""
Multi-School RateMyProfessors Scraper + Cleaner
================================================
Scrapes Broward College (BC), Florida Atlantic University (FAU),
and Florida International University (FIU) from RateMyProfessors,
then merges and cleans into a single CSV with pathway mapping.

Usage:
    python all_schools_rmp.py
    # or in Google Colab: paste into a cell and run
"""

import requests, csv, time, json, sys, string
from collections import defaultdict

# ==========================================================================
# CONFIG
# ==========================================================================
GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
OUTPUT_FILE = "all_schools_rmp_cleaned.csv"

HEADERS = {
    "Authorization": "Basic dGVzdDp0ZXN0",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Referer": "https://www.ratemyprofessors.com/",
}

SCHOOLS_TO_SCRAPE = [
    "Broward College",
    "Florida Atlantic University",
    "Florida International University",
]

# ==========================================================================
# PATHWAY MAPS — keys are RMP department strings, values are pathway labels
# Add any unmapped departments printed at the end into the appropriate list.
# ==========================================================================

_BC_PATHWAY_MAP = {
    "Arts, Humanities, Communication & Design": [
        "Architecture", "Art", "Art History", "Communication", "Dance", "English",
        "English As A Second Language", "Film", "Fine Arts", "Graphic Arts",
        "Humanities", "Journalism", "Languages", "Literature", "Music",
        "Performing Arts", "Photography", "Philosophy", "Reading", "Religion",
        "Spanish", "Speech", "Theater", "Visual & Performing Arts", "Visual Arts",
        "Writing",
    ],
    "Business": [
        "Accounting", "Business", "Business  Finance", "Business & Finance",
        "Business Administration", "Economics", "Finance", "Management",
        "Marketing", "Paralegal Studies", "Supervisory Management",
    ],
    "Education": [
        "Education", "Continuing Education", "Strategies For Success",
        "Student Success",
    ],
    "Health Sciences": [
        "Anatomy", "Chiropractic Education", "Health", "Health Science",
        "Medicine", "Nursing", "Nutrition", "Physical Therapy",
        "Radiation Therapy Technology", "Wellness", "Physical Education",
        "Physical Ed",
    ],
    "Industry, Manufacturing, Construction & Transportation": [
        "Aviation", "Civil Engineering", "Mechanical Engineering",
    ],
    "Institute of Public Safety": [
        "Criminal Justice", "Criminology", "Law",
    ],
    "STEM": [
        "Biological Sciences", "Biology", "Chemistry", "Computer Science",
        "Engineering", "Geology", "Information Science", "Information Technology",
        "Mathematics", "Natural Sciences", "Physical Sciences", "Physics",
        "Science", "Statistics",
    ],
    "Social Behavioral Sciences & Human Services": [
        "Anthropology", "Behavioral Sciences", "Ethnic Studies", "Geography",
        "History", "History  Political Science", "History & Political Science",
        "History amp Political Science", "Human Relations", "International Studies",
        "Political Science", "Psychology", "Social Science", "Social Studies",
        "Social Work", "Sociology", "Women's Studies",
    ],
}

_FAU_PATHWAY_MAP = {
    "Arts, Humanities, Communication & Design": [
        "Architecture", "Art", "Art History", "Communication", "Communications",
        "Dance", "English", "Film", "Fine Arts", "Graphic Design", "Humanities",
        "Journalism", "Languages", "Latin American Studies", "Linguistics",
        "Literature", "Media Studies", "Music", "Performing Arts", "Philosophy",
        "Photography", "Religion", "Spanish", "Speech", "Theater",
        "Theatre", "Visual Arts", "Writing", "French", "German", "Italian",
        "Portuguese", "Chinese", "Japanese", "Hebrew", "Arabic",
    ],
    "Business": [
        "Accounting", "Business", "Business Administration", "Economics",
        "Finance", "Hospitality", "Management", "Marketing",
        "Real Estate", "Taxation", "Supply Chain Management",
        "International Business",
    ],
    "Education": [
        "Education", "Educational Leadership", "Exceptional Education",
        "Physical Education", "Teaching",
    ],
    "Health Sciences": [
        "Anatomy", "Health", "Health Administration", "Health Science",
        "Medicine", "Nursing", "Nutrition", "Physical Therapy",
        "Psychology", "Public Health", "Social Work", "Wellness",
        "Biomedical Science", "Clinical Mental Health Counseling",
        "Occupational Therapy",
    ],
    "Industry, Manufacturing, Construction & Transportation": [
        "Civil Engineering", "Computer Engineering", "Electrical Engineering",
        "Engineering Technology", "Mechanical Engineering", "Ocean Engineering",
        "Environmental Engineering", "Industrial Engineering",
    ],
    "Institute of Public Safety": [
        "Criminal Justice", "Criminology", "Law", "Legal Studies",
    ],
    "STEM": [
        "Biological Sciences", "Biology", "Chemistry", "Computer Science",
        "Environmental Science", "Geology", "Information Technology",
        "Mathematics", "Natural Sciences", "Neuroscience", "Physics",
        "Science", "Statistics", "Biochemistry", "Marine Biology",
        "Ocean Sciences", "Geosciences",
    ],
    "Social Behavioral Sciences & Human Services": [
        "Anthropology", "Behavioral Sciences", "Ethnic Studies", "Geography",
        "Global Studies", "History", "Human Services", "International Relations",
        "Political Science", "Psychology", "Social Science", "Social Work",
        "Sociology", "Urban Planning", "Women's Studies", "African American Studies",
        "Jewish Studies",
    ],
}

_FIU_PATHWAY_MAP = {
    "Arts, Humanities, Communication & Design": [
        "Architecture", "Art", "Art History", "Communication", "Communications",
        "Dance", "English", "Film", "Fine Arts", "Graphic Design", "Humanities",
        "Interior Architecture", "Journalism", "Landscape Architecture",
        "Languages", "Latin American Studies", "Literature", "Music",
        "Performing Arts", "Philosophy", "Photography", "Religion",
        "Spanish", "Speech", "Theater", "Theatre", "Visual Arts", "Writing",
        "French", "German", "Italian", "Portuguese", "Chinese", "Japanese",
        "Creative Writing", "Media Studies",
    ],
    "Business": [
        "Accounting", "Business", "Business Administration", "Economics",
        "Finance", "Hospitality", "Insurance", "Management", "Marketing",
        "Real Estate", "Taxation", "International Business",
        "Entrepreneurship", "Supply Chain", "Decision Sciences",
    ],
    "Education": [
        "Education", "Curriculum & Instruction", "Educational Leadership",
        "Educational Psychology", "Exceptional Education", "Physical Education",
        "Science Education", "Teaching", "Counselor Education",
    ],
    "Health Sciences": [
        "Anatomy", "Biomedical Engineering", "Dietetics", "Health",
        "Health Administration", "Health Science", "Medicine", "Nursing",
        "Nutrition", "Occupational Therapy", "Physical Therapy",
        "Public Health", "Recreational Therapy", "Wellness",
        "Biomedical Sciences", "Physical Medicine",
    ],
    "Industry, Manufacturing, Construction & Transportation": [
        "Civil Engineering", "Computer Engineering", "Construction Management",
        "Electrical Engineering", "Engineering Technology",
        "Environmental Engineering", "Industrial Engineering",
        "Mechanical Engineering", "Systems Engineering",
    ],
    "Institute of Public Safety": [
        "Criminal Justice", "Criminology", "Law", "Legal Studies",
        "Forensic Science",
    ],
    "STEM": [
        "Biological Sciences", "Biology", "Chemistry", "Computer Science",
        "Earth Sciences", "Environmental Science", "Geosciences",
        "Information Technology", "Mathematics", "Natural Sciences",
        "Neuroscience", "Physics", "Science", "Statistics",
        "Biochemistry", "Marine Biology", "Ecology", "Data Science",
    ],
    "Social Behavioral Sciences & Human Services": [
        "African & African Diaspora Studies", "Anthropology",
        "Asian Studies", "Behavioral Sciences", "Ethnic Studies",
        "Geography", "Global Studies", "History", "Human Services",
        "International Relations", "Jewish Studies", "Political Science",
        "Psychology", "Social Science", "Social Work", "Sociology",
        "Urban Studies", "Women's & Gender Studies", "Latin American Studies",
    ],
}

_SCHOOL_PATHWAY_MAPS = {
    "broward college": _BC_PATHWAY_MAP,
    "florida atlantic university": _FAU_PATHWAY_MAP,
    "florida international university": _FIU_PATHWAY_MAP,
}

def _build_lookup(pathway_map):
    lookup = {}
    for pathway, depts in pathway_map.items():
        for dept in depts:
            lookup[dept.lower()] = pathway
    return lookup

_SCHOOL_LOOKUPS = {
    school: _build_lookup(pm) for school, pm in _SCHOOL_PATHWAY_MAPS.items()
}


# ==========================================================================
# RMP API HELPERS
# ==========================================================================

def get_school_ids(school_name):
    payload = {
        "query": (
            "query NewSearchSchoolsQuery($query: SchoolSearchQuery!) {"
            "  newSearch {"
            "    schools(query: $query) {"
            "      edges { cursor node { id legacyId name city state } }"
            "      pageInfo { hasNextPage endCursor }"
            "    }"
            "  }"
            "}"
        ),
        "variables": {"query": {"text": school_name}},
    }
    resp = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"  HTTP {resp.status_code}: {resp.text[:300]}")
        return []
    data = resp.json()
    edges = data.get("data", {}).get("newSearch", {}).get("schools", {}).get("edges", [])
    matches = []
    for edge in edges:
        node = edge["node"]
        if school_name.lower() in node["name"].lower():
            label = f"{node['name']} - {node['city']}, {node['state']}"
            print(f"  Found: {label}  (legacyId={node['legacyId']})")
            matches.append((node["id"], node["legacyId"], label))
    return matches


def _search_teachers(school_id, search_text):
    QUERY = (
        "query NewSearchTeachersQuery("
        "  $query: TeacherSearchQuery!, $count: Int!, $cursor: String"
        ") {"
        "  newSearch {"
        "    teachers(query: $query, first: $count, after: $cursor) {"
        "      edges {"
        "        cursor"
        "        node {"
        "          id legacyId firstName lastName"
        "          school { name id }"
        "          department"
        "          avgRating numRatings avgDifficulty"
        "          wouldTakeAgainPercent"
        "          teacherRatingTags { tagName tagCount }"
        "          ratingsDistribution { r1 r2 r3 r4 r5 total }"
        "        }"
        "      }"
        "      pageInfo { hasNextPage endCursor }"
        "    }"
        "  }"
        "}"
    )
    results, cursor = [], ""
    while True:
        payload = {
            "query": QUERY,
            "variables": {
                "query": {"text": search_text, "schoolID": school_id},
                "count": 100,
                "cursor": cursor,
            },
        }
        resp = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=30)
        if resp.status_code != 200:
            break
        body = resp.json()
        teachers = body.get("data", {}).get("newSearch", {}).get("teachers")
        if teachers is None:
            break
        for edge in teachers["edges"]:
            results.append(edge["node"])
        if not teachers["pageInfo"]["hasNextPage"]:
            break
        cursor = teachers["pageInfo"]["endCursor"]
        time.sleep(0.3)
    return results


def _fetch_rating_details(professor_id):
    QUERY = (
        "query TeacherRatingsPageQuery($id: ID!, $count: Int!, $cursor: String) {"
        "  node(id: $id) {"
        "    ... on Teacher {"
        "      ratings(first: $count, after: $cursor) {"
        "        edges { node { class date } }"
        "        pageInfo { hasNextPage endCursor }"
        "      }"
        "    }"
        "  }"
        "}"
    )
    courses, dates, cursor = set(), [], None
    while True:
        payload = {
            "query": QUERY,
            "variables": {"id": professor_id, "count": 100, "cursor": cursor},
        }
        try:
            resp = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=30)
            if resp.status_code != 200:
                break
            body = resp.json()
            node = body.get("data", {}).get("node")
            if not node or "ratings" not in node:
                break
            for edge in node["ratings"]["edges"]:
                rn = edge["node"]
                c = rn.get("class", "").strip()
                if c:
                    courses.add(c)
                d = rn.get("date", "").strip()
                if d:
                    dates.append(d[:10])
            if not node["ratings"]["pageInfo"]["hasNextPage"]:
                break
            cursor = node["ratings"]["pageInfo"]["endCursor"]
            time.sleep(0.2)
        except Exception as e:
            print(f"    WARN: {e}")
            break
    return sorted(courses), (min(dates) if dates else ""), (max(dates) if dates else "")


def fetch_all_professors(school_id, school_label):
    seen_ids, professors = set(), []
    search_terms = [""] + list(string.ascii_lowercase)
    for i, letter in enumerate(search_terms):
        label = f"'{letter}'" if letter else "(blank)"
        raw = _search_teachers(school_id, letter)
        new_count = 0
        for n in raw:
            pid = n["id"]
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            new_count += 1
            wta = n.get("wouldTakeAgainPercent")
            raw_tags = n.get("teacherRatingTags") or []
            tags_str = "; ".join(
                f"{t['tagName']} ({t['tagCount']})"
                for t in raw_tags if t.get("tagCount", 0) > 0
            )
            dist = n.get("ratingsDistribution") or {}
            professors.append({
                "school": school_label,
                "first_name": n["firstName"],
                "last_name": n["lastName"],
                "department": n.get("department", ""),
                "avg_rating": n.get("avgRating", 0),
                "num_ratings": n.get("numRatings", 0),
                "avg_difficulty": n.get("avgDifficulty", 0),
                "would_take_again_pct": (
                    round(wta, 1) if wta is not None and wta >= 0 else None
                ),
                "tags": tags_str,
                "r1": dist.get("r1", 0), "r2": dist.get("r2", 0),
                "r3": dist.get("r3", 0), "r4": dist.get("r4", 0),
                "r5": dist.get("r5", 0),
                "_id": pid,
                "_num_ratings": n.get("numRatings", 0),
            })
        print(f"  [{i+1}/{len(search_terms)}] search={label:8s}  "
              f"returned {len(raw):4d}  new {new_count:4d}  total {len(professors)}")
        time.sleep(0.3)
    return professors


def fetch_course_codes(professors):
    rated = [p for p in professors if p["_num_ratings"] > 0]
    print(f"\n  Fetching course codes for {len(rated)} rated professors "
          f"(~{len(rated) * 0.3 / 60:.0f} min)...")
    for i, p in enumerate(rated):
        courses, earliest, most_recent = _fetch_rating_details(p["_id"])
        p["courses"] = "; ".join(courses)
        p["earliest_rating"] = earliest
        p["most_recent_rating"] = most_recent
        if (i + 1) % 100 == 0 or (i + 1) == len(rated):
            print(f"    [{i+1}/{len(rated)}] fetched")
    for p in professors:
        p.setdefault("courses", "")
        p.setdefault("earliest_rating", "")
        p.setdefault("most_recent_rating", "")


# ==========================================================================
# CLEAN + MERGE
# ==========================================================================

def _parse_tags(tags_str):
    tags = {}
    if not tags_str:
        return tags
    for part in tags_str.split("; "):
        part = part.strip()
        if not part:
            continue
        idx = part.rfind("(")
        if idx > 0 and part.endswith(")"):
            name = part[:idx].strip()
            try:
                tags[name] = tags.get(name, 0) + int(part[idx+1:-1])
            except ValueError:
                pass
    return tags


def _format_tags(tags_dict):
    if not tags_dict:
        return ""
    return "; ".join(f"{n} ({c})" for n, c in sorted(tags_dict.items(), key=lambda x: -x[1]))


def _map_dept_to_pathway(dept_str, school_name_lower):
    lookup = _SCHOOL_LOOKUPS.get(school_name_lower, {})
    depts = [d.strip() for d in dept_str.split(";")]
    pathways, unmapped = [], []
    for d in depts:
        p = lookup.get(d.lower())
        if p is None:
            if d not in ("", "Administration", "Advising", "Not Specified",
                         "Select department"):
                unmapped.append(d)
            p = "Other"
        if p not in pathways:
            pathways.append(p)
    return "; ".join(pathways), unmapped


def clean_and_merge(professors):
    """Deduplicate, merge multi-dept rows, map pathways, return list of dicts."""
    # Normalize names
    for p in professors:
        p["first_name"] = p["first_name"].strip().title()
        p["last_name"]  = p["last_name"].strip().title()
        p["department"] = p["department"].strip().replace("\t", "")

    # Group by (school, first, last) for merging
    groups = defaultdict(list)
    for p in professors:
        key = (p["school"].lower(), p["first_name"].lower(), p["last_name"].lower())
        groups[key].append(p)

    merged_rows, all_unmapped = [], []

    for (school_lower, _, _), group in groups.items():
        if len(group) == 1:
            row = dict(group[0])
        else:
            row = dict(group[0])
            # Combined departments
            all_depts = []
            for p in group:
                for d in p["department"].split(";"):
                    d = d.strip()
                    if d and d not in all_depts:
                        all_depts.append(d)
            row["department"] = "; ".join(all_depts)

            # Weighted averages
            total_n = weighted_r = weighted_d = weighted_w = wta_n = 0.0
            for p in group:
                n = float(p["num_ratings"] or 0)
                if n > 0:
                    total_n    += n
                    weighted_r += float(p["avg_rating"] or 0) * n
                    weighted_d += float(p["avg_difficulty"] or 0) * n
                    wta = p.get("would_take_again_pct")
                    if wta is not None:
                        weighted_w += float(wta) * n
                        wta_n += n

            row["avg_rating"]         = round(weighted_r / total_n, 1) if total_n > 0 else 0
            row["num_ratings"]        = int(total_n)
            row["avg_difficulty"]     = round(weighted_d / total_n, 1) if total_n > 0 else 0
            row["would_take_again_pct"] = round(weighted_w / wta_n, 1) if wta_n > 0 else None

            # Merge tags
            combined_tags = {}
            for p in group:
                for name, count in _parse_tags(p.get("tags", "")).items():
                    combined_tags[name] = combined_tags.get(name, 0) + count
            row["tags"] = _format_tags(combined_tags)

            # Sum rating distribution
            for k in ("r1", "r2", "r3", "r4", "r5"):
                row[k] = sum(int(p.get(k) or 0) for p in group)

            # Merge courses
            all_courses = set()
            for p in group:
                for c in p.get("courses", "").split(";"):
                    c = c.strip()
                    if c:
                        all_courses.add(c)
            row["courses"] = "; ".join(sorted(all_courses))

            # Date range
            earliests   = [p["earliest_rating"] for p in group if p.get("earliest_rating")]
            most_recent = [p["most_recent_rating"] for p in group if p.get("most_recent_rating")]
            row["earliest_rating"]   = min(earliests)   if earliests   else ""
            row["most_recent_rating"] = max(most_recent) if most_recent else ""

        # Map pathway
        pathway_str, unmapped = _map_dept_to_pathway(row["department"], school_lower)
        all_unmapped.extend(unmapped)
        row["pathway"] = pathway_str

        # Clean up internals
        row.pop("_id", None)
        row.pop("_num_ratings", None)

        merged_rows.append(row)

    if all_unmapped:
        unique_unmapped = sorted(set(all_unmapped))
        print(f"\n  ⚠  Unmapped departments (set to 'Other') — add to script to fix:")
        for d in unique_unmapped:
            print(f"       - {d}")

    merged_rows.sort(key=lambda r: (r["school"], r["last_name"].lower(), r["first_name"].lower()))
    return merged_rows


# ==========================================================================
# MAIN
# ==========================================================================

COLS = [
    "school", "first_name", "last_name", "pathway",
    "avg_rating", "num_ratings", "avg_difficulty", "would_take_again_pct",
    "tags", "r1", "r2", "r3", "r4", "r5",
    "courses", "earliest_rating", "most_recent_rating",
]


def main():
    all_professors = []

    for school_name in SCHOOLS_TO_SCRAPE:
        print(f"\n{'='*60}")
        print(f"  Scraping: {school_name}")
        print(f"{'='*60}")
        schools = get_school_ids(school_name)
        if not schools:
            print(f"  ⚠ Could not find '{school_name}' — skipping.")
            continue

        for gql_id, legacy_id, label in schools:
            print(f"\n  --- {label} (legacyId={legacy_id}) ---")
            profs = fetch_all_professors(gql_id, school_name)
            all_professors.extend(profs)

    if not all_professors:
        sys.exit("No professors found. The API may have changed.")

    print(f"\n[Course codes] Fetching for all {len(all_professors)} professors...")
    fetch_course_codes(all_professors)

    print("\n[Cleaning & merging]...")
    rows = clean_and_merge(all_professors)

    print(f"\n[Writing] {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    rated = sum(1 for r in rows if r["num_ratings"] and int(r["num_ratings"]) > 0)
    print(f"\n  Done! {len(rows)} professors ({rated} with ratings) → {OUTPUT_FILE}")

    # Auto-download in Google Colab
    try:
        from google.colab import files
        files.download(OUTPUT_FILE)
        print("  Download started!")
    except ImportError:
        pass


if __name__ == "__main__":
    main()

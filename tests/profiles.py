"""State profiles for the tests, shaped like the site's state/<slug>/profile.json."""
import json

NORTHMARK = {"name": "Northmark", "slug": "northmark", "postalCode": "NQ", "fipsCode": "98",
             "fccCallDistrict": "0", "neighborPostalCodes": ["NR", "NS"]}

# The state block of the site's state/indiana/profile.json, as it is today.
SITE_INDIANA = {"name": "Indiana", "slug": "indiana", "postalCode": "IN", "fipsCode": "18",
                "demonym": "Hoosier", "countyCount": 92, "governmentDomain": "in.gov",
                "fccCallDistrict": "9", "neighborPostalCodes": ["IL", "KY", "MI", "OH"]}


def write_profile(root, state=NORTHMARK, folder=None, **extra):
    """root/state/<folder>/profile.json; returns the state/ folder."""
    states = root / "state"
    path = states / (folder or state.get("slug", "unnamed")) / "profile.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"state": state, **extra}))
    return states

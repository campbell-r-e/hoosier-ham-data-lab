"""Which state the lab's site export is about, read from the site's state profile.

You do not need to change or read this file. With nothing configured it
answers Indiana, so the lab works exactly as it always has.

The website keeps one file describing its state, `state/<slug>/profile.json`,
and every part of the system reads that file rather than keeping its own copy
of the facts. fcc-ham-counts (the service that publishes your answers) reads
it, and `hamstats export` reads the same one, so the document you export is
about the state the service would publish.

Where the profile is, first match wins:

  1. the `location` passed to load(), or
  2. the FCCHAM_STATE_PROFILE environment variable, or
  3. /opt/fcc-ham-counts-state/state, the service's own copy, when it exists,
  4. otherwise INDIANA below, which matches the site's Indiana profile.

A location is either the site's `state/` folder, holding exactly one state's
folder, or a profile.json itself -- the same rule fcc-ham-counts follows
(fccham/state.py). A profile that is named but missing or unsound is an error,
never a quiet fallback to Indiana.

Fields read (all from profile.json; any other field is ignored):

  state.name                  e.g. "Indiana"
  state.slug                  e.g. "indiana"; also the folder's name
  state.postalCode            e.g. "IN", the FCC file's state field
  state.fipsCode              e.g. "18"
  state.fccCallDistrict       e.g. "9"
  state.neighborPostalCodes   e.g. ["IL", "KY", "MI", "OH"]; optional, but
                              the export's neighbors comparison needs it
"""
import dataclasses
import json
import os
import re

ENV_VAR = "FCCHAM_STATE_PROFILE"
SERVICE_LOCATION = "/opt/fcc-ham-counts-state/state"


class ProfileError(ValueError):
    """The state profile is missing, unreadable, or not what the lab needs."""


@dataclasses.dataclass(frozen=True)
class State:
    name: str
    slug: str
    postal_code: str
    fips_code: str
    call_district: str
    neighbors: tuple | None

    def require_neighbors(self):
        """The neighbors, or ProfileError when the profile lists none."""
        if not self.neighbors:
            raise ProfileError(
                f"the state profile for {self.name} has no state.neighborPostalCodes; "
                "the neighbors comparison needs the postal codes of the states that "
                "border it")
        return self.neighbors


# The lab's default, the same facts as the site's state/indiana/profile.json.
# The neighbors keep the order the lab has always asked for them in, so the
# learner's export comes out exactly as before whatever her tie-break does.
INDIANA = State(name="Indiana", slug="indiana", postal_code="IN", fips_code="18",
                call_district="9", neighbors=("IL", "OH", "MI", "KY"))


def _text(value):
    return isinstance(value, str) and value.strip() != ""


def _matches(pattern):
    return lambda value: isinstance(value, str) and re.fullmatch(pattern, value) is not None


def _postal_codes(value):
    return (isinstance(value, list) and len(value) > 0
            and all(_matches(r"[A-Z]{2}")(code) for code in value)
            and len(set(value)) == len(value))


# (dotted path, check, what it must be, required)
FIELDS = [
    ("state.name", _text, "a non-empty string", True),
    ("state.slug", _matches(r"[a-z][a-z0-9-]*"), "lowercase letters, digits and hyphens", True),
    ("state.postalCode", _matches(r"[A-Z]{2}"), "a two-letter postal code such as OH", True),
    ("state.fipsCode", _matches(r"\d{2}"), "a two-digit Census FIPS code such as 39", True),
    ("state.fccCallDistrict", _matches(r"\d"), "one digit, the FCC call district", True),
    ("state.neighborPostalCodes", _postal_codes,
     "a non-empty list of distinct two-letter postal codes", False),
]

_MISSING = object()


def _at(profile, dotted):
    value = profile
    for key in dotted.split("."):
        if not isinstance(value, dict) or key not in value:
            return _MISSING
        value = value[key]
    return value


def configured_location(environ=None):
    """Where the profile is when load() is given no location: the environment
    variable, else the service's copy if it exists, else None (use INDIANA)."""
    environ = os.environ if environ is None else environ
    if environ.get(ENV_VAR):
        return environ[ENV_VAR]
    if os.path.exists(SERVICE_LOCATION):
        return SERVICE_LOCATION
    return None


def profile_path(location):
    """The profile.json that `location` (a state/ folder or the file) names."""
    if os.path.isfile(location):
        return location
    if not os.path.isdir(location):
        raise ProfileError(
            f"no state profile at {location} (set {ENV_VAR} to the site's state/ "
            f"folder or to a profile.json)")
    folders = sorted(name for name in os.listdir(location)
                     if os.path.isdir(os.path.join(location, name)) and not name.startswith("."))
    if len(folders) != 1:
        raise ProfileError(
            f"{location} must hold exactly one state's folder; found {', '.join(folders) or 'none'}")
    return os.path.join(location, folders[0], "profile.json")


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            profile = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ProfileError(f"cannot read the state profile {path}: {exc}") from exc
    if not isinstance(profile, dict):
        raise ProfileError(f"the state profile {path} is not a JSON object")
    return profile


def _problems(profile):
    problems = []
    for dotted, check, want, required in FIELDS:
        value = _at(profile, dotted)
        if value is _MISSING:
            if required:
                problems.append(f"{dotted} is missing: it must be {want}")
        elif not check(value):
            problems.append(f"{dotted} is invalid: it must be {want}")
    return problems


def _check_consistent(state, path):
    folder = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if state["slug"] != folder:
        raise ProfileError(
            f"the state profile {path} does not match its folder: state.slug is "
            f"{state['slug']!r} but the folder is {folder!r}")
    if state["postalCode"] in state.get("neighborPostalCodes", ()):
        raise ProfileError(
            f"the state profile {path} lists its own postal code {state['postalCode']} "
            f"among state.neighborPostalCodes")


def read_profile(location):
    """The State described by the profile at `location`; ProfileError if unsound."""
    path = profile_path(location)
    profile = _read(path)
    problems = _problems(profile)
    if problems:
        raise ProfileError(f"the state profile {path} is incomplete:\n  " + "\n  ".join(problems))
    state = profile["state"]
    _check_consistent(state, path)
    neighbors = state.get("neighborPostalCodes")
    return State(name=state["name"], slug=state["slug"], postal_code=state["postalCode"],
                 fips_code=state["fipsCode"], call_district=state["fccCallDistrict"],
                 neighbors=tuple(neighbors) if neighbors else None)


def load(location=None):
    """The state the lab is about: the profile at `location`, or wherever
    configured_location() finds one, or INDIANA when nothing is configured."""
    location = location or configured_location()
    return read_profile(location) if location else INDIANA

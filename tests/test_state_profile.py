"""Reading the site's state profile: where it is found, what it must hold, and
Indiana when nothing is configured. Northmark (NQ) is a made-up state."""
import json

import pytest

import state_profile
from profiles import NORTHMARK, SITE_INDIANA, write_profile
from state_profile import INDIANA, ProfileError, State


def northmark_with(**changes):
    return {**NORTHMARK, **changes}


def test_reads_the_state_from_the_sites_state_folder(tmp_path):
    assert state_profile.read_profile(str(write_profile(tmp_path))) == State(
        name="Northmark", slug="northmark", postal_code="NQ", fips_code="98",
        call_district="0", neighbors=("NR", "NS"))


def test_reads_a_profile_json_directly_and_ignores_fields_it_does_not_use(tmp_path):
    states = write_profile(tmp_path, site={"domain": "example.invalid"}, _about="text")
    found = state_profile.read_profile(str(states / "northmark" / "profile.json"))
    assert found.postal_code == "NQ"


def test_the_built_in_default_is_the_sites_indiana_profile(tmp_path):
    states = write_profile(tmp_path, SITE_INDIANA)
    assert state_profile.read_profile(str(states)) == INDIANA


def test_neighbors_are_optional_until_they_are_needed(tmp_path):
    state = {k: v for k, v in NORTHMARK.items() if k != "neighborPostalCodes"}
    found = state_profile.read_profile(str(write_profile(tmp_path, state)))
    assert found.neighbors is None
    with pytest.raises(ProfileError, match="Northmark has no state.neighborPostalCodes"):
        found.require_neighbors()
    assert INDIANA.require_neighbors() == ("IL", "KY", "MI", "OH")


def test_a_missing_location_says_how_to_point_at_one(tmp_path):
    with pytest.raises(ProfileError, match="FCCHAM_STATE_PROFILE"):
        state_profile.read_profile(str(tmp_path / "nowhere"))


def test_the_state_folder_must_hold_exactly_one_state(tmp_path):
    (tmp_path / "empty" / ".git").mkdir(parents=True)
    with pytest.raises(ProfileError, match="found none"):
        state_profile.read_profile(str(tmp_path / "empty"))
    states = write_profile(tmp_path)
    (states / "southmark").mkdir()
    with pytest.raises(ProfileError, match="found northmark, southmark"):
        state_profile.read_profile(str(states))


def test_unreadable_or_non_object_json_is_an_error(tmp_path):
    states = write_profile(tmp_path)
    path = states / "northmark" / "profile.json"
    path.write_text("{not json")
    with pytest.raises(ProfileError, match="cannot read"):
        state_profile.read_profile(str(states))
    path.write_text("[]")
    with pytest.raises(ProfileError, match="not a JSON object"):
        state_profile.read_profile(str(states))


def test_every_missing_or_invalid_field_is_named(tmp_path):
    state = northmark_with(postalCode="nq", fipsCode="9", neighborPostalCodes=["NR", "NR"])
    del state["name"]
    with pytest.raises(ProfileError) as caught:
        state_profile.read_profile(str(write_profile(tmp_path, state)))
    message = str(caught.value)
    for problem in ("state.name is missing", "state.postalCode is invalid",
                    "state.fipsCode is invalid", "state.neighborPostalCodes is invalid"):
        assert problem in message


def test_a_profile_without_a_state_block_is_incomplete(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"site": {}}))
    with pytest.raises(ProfileError, match="state.slug is missing"):
        state_profile.read_profile(str(path))


def test_the_slug_must_match_its_folder(tmp_path):
    with pytest.raises(ProfileError, match="does not match its folder"):
        state_profile.read_profile(str(write_profile(tmp_path, folder="southmark")))


def test_a_state_is_not_its_own_neighbor(tmp_path):
    state = northmark_with(neighborPostalCodes=["NR", "NQ"])
    with pytest.raises(ProfileError, match="its own postal code NQ"):
        state_profile.read_profile(str(write_profile(tmp_path, state)))


def test_with_nothing_configured_the_lab_is_about_indiana():
    assert state_profile.configured_location() is None
    assert state_profile.load() == INDIANA


def test_the_environment_variable_names_the_profile(tmp_path, monkeypatch):
    monkeypatch.setenv(state_profile.ENV_VAR, str(write_profile(tmp_path)))
    assert state_profile.load().postal_code == "NQ"


def test_a_named_profile_that_is_missing_never_falls_back_to_indiana(tmp_path, monkeypatch):
    monkeypatch.setenv(state_profile.ENV_VAR, str(tmp_path / "nowhere"))
    with pytest.raises(ProfileError):
        state_profile.load()


def test_the_services_copy_is_used_when_it_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(state_profile, "SERVICE_LOCATION", str(write_profile(tmp_path)))
    assert state_profile.load().postal_code == "NQ"


def test_an_explicit_location_wins_over_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv(state_profile.ENV_VAR, str(tmp_path / "nowhere"))
    assert state_profile.load(str(write_profile(tmp_path))).name == "Northmark"


def test_configured_location_reads_the_environment_it_is_given():
    assert state_profile.configured_location({state_profile.ENV_VAR: "/x/state"}) == "/x/state"
    assert state_profile.configured_location({state_profile.ENV_VAR: ""}) is None

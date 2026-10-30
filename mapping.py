from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class TitleInfo:
    slug: str
    full_name: str
    soundtrack_release_titles: list[str]
    album: str
    artists: list[str]
    variants: list[str] = field(default_factory=list)


unknown_title = TitleInfo(slug="unknown", full_name="[!] Unknown", soundtrack_release_titles=[], album="Unknown",
                          artists=[])

bnk_names = {
    "0129-1ba8": TitleInfo(slug="bl-reckless-forbidden_knowledge", full_name="Reckless, Forbidden Knowledge",
                           soundtrack_release_titles=["Reckless", "Forbidden Knowledge"], album="Beyond Light",
                           artists=["Josh Mosser"]),
    "0129-1ba6": TitleInfo(slug="rw-edz", full_name="EDZ", soundtrack_release_titles=["EDZ"], album="Red War",
                           artists=["Rotem Moav"]),
    "0129-1b9c": TitleInfo(slug="rw-trostland", full_name="Trostland // Emerald Coast // What we fought for",
                           soundtrack_release_titles=[], album="Red War",
                           artists=["Rotem Moav"]),
    "0106-169e": TitleInfo(slug="wq-fear_swells", full_name="Fear Swells, Threshold",
                           soundtrack_release_titles=["Fear Swells", "Threshold"],
                           album="Witch Queen", artists=["Pieter Schlosser"], variants=["0106-0111"]),
    "0106-0111": TitleInfo(slug="wq-fear_swells2", full_name="Fear Swells, Threshold [Variant]",
                           soundtrack_release_titles=["Fear Swells", "Threshold"],
                           album="Witch Queen", artists=["Pieter Schlosser"], variants=["0106-169e"]),
    "0129-04d0": TitleInfo(slug="fs-dreaming_city", full_name="Dreaming City",
                           soundtrack_release_titles=["Dreaming City"], album="Forsaken", artists=["Rotem Moav"]),
    "012b-0ba0": TitleInfo(slug="rw-pathfinder", full_name="Pathfinder", soundtrack_release_titles=["Pathfinder"],
                           album="Red War", artists=["Rotem Moav"], variants=["0129-1bb6", "0129-1bba"]),
    "0129-1bb6": TitleInfo(slug="rw-pathfinder2", full_name="Pathfinder [Variant]",
                           soundtrack_release_titles=["Pathfinder"], album="Red War", artists=["Rotem Moav"],
                           variants=["012b-0ba0", "0129-1bba"]),
    "0129-1bba": TitleInfo(slug="rw-pathfinder3", full_name="Pathfinder [Variant 2]",
                           soundtrack_release_titles=["Pathfinder"], artists=["Rotem Moav"], album="Red War",
                           variants=["0129-1bb6", "012b-0ba0"]),
    "0129-1bae": TitleInfo(slug="rw-rise", full_name="Rise", soundtrack_release_titles=["Rise"], album="Red War",
                           artists=["C Paul Johnson"]),
    "0129-1bc2": TitleInfo(slug="rw-lost_sector", full_name="Lost Sector", soundtrack_release_titles=["Lost Sector"],
                           album="Red War", artists=["Pieter Schlosser"], variants=["012b-0ba6"]),
    "012b-0ba6": TitleInfo(slug="rw-lost_sector2", full_name="Lost Sector [Variant]",
                           soundtrack_release_titles=["Lost Sector"],
                           album="Red War", artists=["Pieter Schlosser"], variants=["0129-1bc2"]),
    "012b-0ba3": TitleInfo(slug="rw-scavengers_den", full_name="Scavengers Den",
                           soundtrack_release_titles=["Scavengers Den"], album="Red War", artists=["Skye Lewin"]),
    "0129-1b9a": TitleInfo(slug="rw-what_we_fight_for", full_name="What We Fight For",
                           soundtrack_release_titles=["What We Fight For"], album="Red War", artists=["Rotem Moav"]),
    "0129-1bd6": TitleInfo(slug="rw-nessus", full_name="Nessus", soundtrack_release_titles=["Nessus"], album="Red War",
                           artists=["C Paul Johnson"]),
    "0129-1bca": TitleInfo(slug="rw-cistern", full_name="Six", soundtrack_release_titles=[], album="Red War",
                           artists=["Rotem Moav"]),
    "0129-1bd2": TitleInfo(slug="rw-orrery", full_name="The Orrery", soundtrack_release_titles=[], album="Red War",
                           artists=[]),  # unknown
    "012b-13d2": TitleInfo(slug="rw-leviathan", full_name="Leviathan", soundtrack_release_titles=["Leviathan"],
                           album="Red War", artists=["Pieter Schlosser"]),
    "012b-13e1": TitleInfo(slug="wq-unknown1", full_name="WQ Unknown", soundtrack_release_titles=[],
                           album="Witch Queen", artists=[]),
    "012b-13fe": unknown_title,
    "012b-1409": unknown_title,
    "0106-010c": unknown_title,
    "0106-0104": TitleInfo(slug="wq-underworld", full_name="Underworld", soundtrack_release_titles=["Underworld"],
                           album="Witch Queen", artists=["Rotem Moav"]),
    "0106-0109": unknown_title,
    "0106-0154": TitleInfo(slug="wq-queens_deception", full_name="Queen's Deception",
                           soundtrack_release_titles=["Queen's Deception"], album="Witch Queen",
                           artists=["Michael Sechrist"]),
    "0106-167a": unknown_title,  # maybe nessus? maybe wq?
    "0106-167d": TitleInfo(slug="wq-yours_to_win", full_name="Yours to Win", soundtrack_release_titles=["Yours to Win"],
                           album="Witch Queen", artists=["Rotem Moav"]),
    "0106-1682": TitleInfo(slug="wq-lepidopterophobia", full_name="Lepidopterophobia, Lucent World",
                           soundtrack_release_titles=["Lepidopterophobia", "Lucent World"], album="Witch Queen",
                           artists=["Skye Lewin"]),
    "0106-1699": TitleInfo(slug="wq-aberrant_path", full_name="Aberrant Path",
                           soundtrack_release_titles=["Aberrant Path"], album="Witch Queen",
                           artists=["Michael Salvatori"]),
    "0129-0f0f": unknown_title,  # witch queen?
    "0129-0f1a": unknown_title,  # wq? has a very distinct e-guitar part in the high-action
    "0129-0f1c": unknown_title,
    "0129-0f1e": unknown_title,  # holy moly I have no clue
    "0129-0f8b": unknown_title,
    "0129-0f8d": unknown_title,
    "0129-0f09": unknown_title,
    "0129-0f13": unknown_title,
    "0129-0f16": unknown_title,
    "0129-0f22": unknown_title,
    "0129-0f24": unknown_title,
    "0129-0f87": unknown_title,  # has some cabal red war vibes
    "0129-0f93": TitleInfo(slug="rw-resist_the_legion", full_name="Resist the Legion",
                           soundtrack_release_titles=["Resist the Legion"],
                           album="Red War", artists=["Skye Lewin"]),  # high action is missing
    "0129-0ff7": TitleInfo(slug="rw-legions_march", full_name="Legion's March",
                           soundtrack_release_titles=["Legion's March"], album="Red War",
                           artists=["Rotem Moav"]),  # the default part is not the one from the soundtrack
    "0129-0ffb": unknown_title,  # cabal?
    "0129-0fff": unknown_title,
    "0129-1b7a": TitleInfo(slug="bl-replicate", full_name="Replicate, Buried Secrets",
                           soundtrack_release_titles=["Replicate", "Buried Secrets"], album="Beyond Light",
                           artists=["Josh Mosser"]),
    "0129-1b7e": TitleInfo(slug="bl-peril_unknown", full_name="Peril Unknown, New Beginnings",
                           soundtrack_release_titles=["Peril Unknown", "New Beginnings"], album="Beyond Light",
                           artists=["Rotem Moav"], variants=["0129-1b88"]),
    "0129-1b88": TitleInfo(slug="bl-peril_unknown2", full_name="Peril Unknown, New Beginnings",
                           soundtrack_release_titles=["Peril Unknown", "New Beginnings"], album="Beyond Light",
                           artists=["Rotem Moav"], variants=["0129-1b7e"]),
    "0129-1b8a": TitleInfo(slug="bl-lament", full_name="Lament, Frigid Tomb",
                           soundtrack_release_titles=["Lament", "Frigid Tomb"], album="Beyond Light",
                           artists=["Michael Sechrist"]),
    "0129-1b84": TitleInfo(slug="bl-whiteout", full_name="Whiteout", soundtrack_release_titles=["Whiteout"],
                           album="Beyond Light", artists=["Skye Lewin"]),
    "0129-1b90": TitleInfo(slug="bl-acceptance", full_name="Acceptance", soundtrack_release_titles=["Acceptance"],
                           album="Beyond Light", artists=["Michael Salvatori"]),
    "0129-1b94": TitleInfo(slug="bl-resistance", full_name="Resistance, Trepidation",
                           soundtrack_release_titles=["Resistance", "Trepidation"],
                           album="Beyond Light", artists=["Rotem Moav"], variants=["0129-1b96"]),
    "0129-1b96": TitleInfo(slug="bl-resistance2", full_name="Resistance, Trepidation",
                           soundtrack_release_titles=["Resistance", "Trepidation"],
                           album="Beyond Light", artists=["Rotem Moav"], variants=["0129-1b94"]),
    # "0129-1ba2": unknown_title,  # unreadable?
    "0129-1bb2": unknown_title,
    "0129-1bbe": unknown_title,  # sounds vexy


}

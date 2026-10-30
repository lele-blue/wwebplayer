from __future__ import annotations

import io
import json
import os.path
import subprocess
import weakref
import xml.etree.ElementTree as ElemT
from _weakref import ReferenceType
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Any, Dict, TypeVar, Generic, Optional, cast, Iterator, IO, Tuple, Set
from xml.etree.ElementTree import Element as OriginalElement

import pydub

# main_args = {"in": "/../bnk/parsed/0129-1ba8.bnk.xml", "out": "./beyond_light_tension1.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1ba6.bnk.xml", "out": "./edz.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1b9c.bnk.xml", "out": "./mavic_square.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0106-169e.bnk.xml", "out": "./fear_swells.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1bae.bnk.xml", "out": "./vanilla_rl_high_action3.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1bb6.bnk.xml", "out": "./vanilla_rl_high_action2.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1bba.bnk.xml", "out": "./vanilla_rl_high_action.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1bc2.bnk.xml", "out": "./vanilla_edz_high_action_some.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1bca.bnk.xml", "out": "./nessus_groove.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1bd2.bnk.xml", "out": "./nessus_small.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1bd6.bnk.xml", "out": "./nessus2.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/012b-0ba0.bnk.xml", "out": "./some_vanilla.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1bd6.bnk.xml", "out": "./nessus.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/012b-0ba6.bnk.xml", "out": "./some_boss.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-04d0.bnk.xml", "out": "./dreaming_city.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/012b-0ba3.bnk.xml", "out": "./scavengers_den.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1b9a.bnk.xml", "out": "./what_we_fight_for.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/012b-13d2.bnk.xml", "out": "./leviathan.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-1b8a.bnk.xml", "out": "./bl-lament.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-0ff7.bnk.xml", "out": "./rw-legions_march.bnkbdl"}
# main_args = {"in": "/../bnk/parsed/0129-0f93.bnk.xml", "out": "./rw-resist_the_legion.bnkbdl"}
main_args = {"in": "/../bnk/parsed/0106-167d.bnk.xml", "out": "./wq-yours_to_win.bnkbdl"}

class Element(OriginalElement):
    """
    Helper class to silence mypy about find not always returning an element.
    When the child node is not found, in most cases we want the program to crash anyway, so it might just be an
    AttributeError, so we don't have to null-check every find call
    """

    def find(self, path: str, *args, **kwargs) -> "Element":
        return cast(Element, super().find(path, *args, **kwargs))

    def findall(self, path: str, namespaces: dict[str, str] | None = None) -> List["Element"]:  # type: ignore
        return cast(List[Element], super().findall(path, namespaces))

    def __iter__(self) -> Iterator["Element"]:
        return cast(Iterator, super())


T = TypeVar("T")

tree = ElemT.parse(os.path.dirname(__file__) + main_args["in"])
root = tree.getroot()


class PendingLink(Generic[T]):
    """
    Creates a weak link that doesn't have to be fulfilled at init (or at all)
    """
    _ready_ids: Dict[str, ReferenceType[T]] = {}

    @classmethod
    def report_ready(cls, id_: str, instance: Any):
        cls._ready_ids[id_] = weakref.ref(instance)

    def __init__(self, t_id: str):
        self.waitingFor = t_id

    def __json__(self):
        return {"refTo": self.waitingFor}

    @property
    def is_ready(self):
        return bool(self.waitingFor in self._ready_ids and self._ready_ids[self.waitingFor]())

    @property
    def ref(self) -> T:
        if not self.is_ready:
            raise ReferenceError("PendingLink has not been resolved yet.")
        value = self._ready_ids[self.waitingFor]()
        if not value:
            raise ReferenceError("Link target has been deleted")
        return value


class HIRCNode:
    __serialize__ = ["id"]

    def __init__(self, id_: str):
        self.id: str = id_


@dataclass
class TrimOffsets:
    __serialize__ = ["__all__"]
    start: float
    end: float


class ClipAutomationType(Enum):
    Volume = 0x00
    FadeIn = 0x03
    FadeOut = 0x04
    Unknown = None

    @classmethod
    def _missing_(cls, value):
        print(f"Unknown {cls.__name__} value 0x{value:02x}")
        return cls.Unknown


class RandomSequencePlaylistType(Enum):
    NoneType = -0x01
    ContinuousSequence = 0x00
    StepSequence = 0x01
    ContinuousRandom = 0x02
    StepRandom = 0x03


class Interpolation(Enum):
    Sine = 0x01
    Log1 = 0x02
    Linear = 0x04
    SCurve = 0x05
    Exp1 = 0x06
    SineRecip = 0x07
    Constant = 0x09
    Unknown = None

    @classmethod
    def _missing_(cls, value):
        print(f"Unknown {cls.__name__} value 0x{value:02x}")
        return cls.Unknown


@dataclass
class GraphPoint:
    __serialize__ = ["__all__"]
    start: float
    end: float
    interpolation: Interpolation


@dataclass
class ClipAutomation:
    __serialize__ = ["__all__"]
    type: ClipAutomationType
    points: List[GraphPoint]


class SyncType(Enum):
    Immediate = 0x00
    NextGrid = 0x01
    NextBar = 0x02
    NextMarker = 0x04
    ExitMarker = 0x07
    Unknown = None

    @classmethod
    def _missing_(cls, value):
        return cls.Unknown


class JumpToType(Enum):
    StartOfPlaylist = 0x00
    # jump_to_id must be set for SpecificItem
    SpecificItem = 0x01
    Unknown = None

    @classmethod
    def _missing_(cls, value):
        return cls.Unknown


@dataclass
class TransitionSourceRule:
    __serialize__ = ["__all__"]
    time: int
    curve: Interpolation
    fade_offset: int
    sync_type: SyncType


@dataclass
class FadeParams:
    __serialize__ = ["__all__"]
    time: int
    curve: Interpolation
    fade_offset: int


class TransitionDestinationEntryType(Enum):
    EntryMarker = 0x00
    SameTime = 0x01
    RandomMarker = 0x02
    RandomUserMarker = 0x03


@dataclass
class TransitionDestinationRule:
    __serialize__ = ["__all__"]
    time: int
    curve: Interpolation
    fade_offset: int
    entry_type: TransitionDestinationEntryType
    # figure out what this does
    jump_to_type: JumpToType
    jump_to: Optional[PendingLink[HIRCNode]] = None


@dataclass
class TransitionRule:
    __serialize__ = ["source_rule", "destination_rule", "source", "destination", "segment", "segment_fade_in",
                     "segment_fade_out", "is_noop"]

    source_rule: TransitionSourceRule
    destination_rule: TransitionDestinationRule
    source: Optional[PendingLink[HIRCNode]] = None
    destination: Optional[PendingLink[HIRCNode]] = None
    segment: Optional[PendingLink["MusicSegment"]] = None
    segment_fade_in: Optional[FadeParams] = None
    segment_fade_out: Optional[FadeParams] = None

    @classmethod
    def from_node(cls, node: Element):
        dst_rule_jump_to_id = node.find("obj[@na='AkMusicTransDstRule']/fld[@na='uJumpToID']").attrib["va"]
        instance = cls(
            TransitionSourceRule(
                time=int(node.find("obj[@na='AkMusicTransSrcRule']/fld[@na='transitionTime']").attrib["va"]),
                curve=Interpolation(
                    int(node.find("obj[@na='AkMusicTransSrcRule']/fld[@na='eFadeCurve']").attrib["va"])),
                fade_offset=int(node.find("obj[@na='AkMusicTransSrcRule']/fld[@na='iFadeOffset']").attrib["va"]),
                sync_type=SyncType(int(node.find("obj[@na='AkMusicTransSrcRule']/fld[@na='eSyncType']").attrib["va"]))
            ),
            TransitionDestinationRule(
                time=int(node.find("obj[@na='AkMusicTransDstRule']/fld[@na='transitionTime']").attrib["va"]),
                curve=Interpolation(
                    int(node.find("obj[@na='AkMusicTransDstRule']/fld[@na='eFadeCurve']").attrib["va"])),
                fade_offset=int(node.find("obj[@na='AkMusicTransDstRule']/fld[@na='iFadeOffset']").attrib["va"]),
                jump_to_type=JumpToType(
                    int(node.find("obj[@na='AkMusicTransDstRule']/fld[@na='eJumpToType']").attrib["va"])),
                jump_to=PendingLink[HIRCNode](dst_rule_jump_to_id) if dst_rule_jump_to_id != "0" else None,
                entry_type=TransitionDestinationEntryType(int(node.find("obj[@na='AkMusicTransDstRule']/fld[@na='eEntryType']").attrib["va"]))
            )
        )

        if node.find("obj[@na='AkMusicTransDstRule']/fld[@na='eEntryType']").attrib["va"] == '1':
            print("[WARN] SameTime Transition converted to EntryMarker, transition will still work but will take significantly longer")
        elif node.find("obj[@na='AkMusicTransDstRule']/fld[@na='eEntryType']").attrib["va"] != '0':
            print("[WARN] Entry type is not EntryMarker or SameTime, transition may sound borked or take really long")

        source_id = node.find("fld[@na='srcID']").attrib["va"]
        destination_id = node.find("fld[@na='dstID']").attrib["va"]
        if source_id != "-1":
            instance.source = PendingLink(source_id)
        if destination_id != "-1":
            instance.destination = PendingLink(destination_id)

        if node.find("fld[@na='AllocTransObjectFlag']").attrib["vf"] == "0x01":
            node = node.find("obj[@na='AkMusicTransitionObject']")
            instance.segment = PendingLink(node.find("fld[@na='segmentID']").attrib["va"])
            instance.segment_fade_in = FadeParams(
                time=int(node.find("obj[@na='fadeInParams']/fld[@na='transitionTime']").attrib["va"]),
                curve=Interpolation(int(node.find("obj[@na='fadeInParams']/fld[@na='eFadeCurve']").attrib["va"])),
                fade_offset=int(node.find("obj[@na='fadeInParams']/fld[@na='iFadeOffset']").attrib["va"])
            )
            instance.segment_fade_out = FadeParams(
                time=int(node.find("obj[@na='fadeOutParams']/fld[@na='transitionTime']").attrib["va"]),
                curve=Interpolation(int(node.find("obj[@na='fadeOutParams']/fld[@na='eFadeCurve']").attrib["va"])),
                fade_offset=int(node.find("obj[@na='fadeOutParams']/fld[@na='iFadeOffset']").attrib["va"])
            )

        return instance

    @property
    def is_noop(self):
        return not self.source and not self.destination


@dataclass
class MusicTrackSource:
    __serialize__ = ["sourceId", "hasSource", "playAt", "trimOffsets", "duration"]
    sourceFormatTypes = {'262145': 'VORBIS'}
    sourceId: str
    hasSource: bool
    playAt: float
    trimOffsets: TrimOffsets
    duration: float

    @classmethod
    def from_node(cls, elem: Element, src_info_elem: Element):
        # language=xpath
        if elem.find("fld[@na='ulPluginID']").attrib["va"] not in cls.sourceFormatTypes:
            # language=
            raise HIRCParser.ParsingException("Unknown Media Type, this is likely a custom plugin")

        # language=xpath
        return cls(
            elem.find("obj[@na='AkMediaInformation']/fld[@na='sourceID']").attrib["va"],
            elem.find("obj[@na='AkMediaInformation']/fld[@na='uSourceBits']/fld[@na='bHasSource']").attrib["va"] == 1,
            float(src_info_elem.find("fld[@na='fPlayAt']").attrib["va"]),
            TrimOffsets(
                start=float(src_info_elem.find("fld[@na='fBeginTrimOffset']").attrib["va"]),
                end=float(src_info_elem.find("fld[@na='fEndTrimOffset']").attrib["va"]),
            ),
            float(src_info_elem.find("fld[@na='fSrcDuration']").attrib["va"]),
        )


class MusicTrack(HIRCNode):
    NodeTypeID = '11'

    __serialize__ = ["automations", "sectionSize", "sourcesCount", "sources", "parent",
                     "id"]

    def __init__(self, node: Element):
        self.automations: List[ClipAutomation] = []
        self._node: Element = node
        self.sectionSize: int
        self.sourcesCount: int
        self.sources: List[MusicTrackSource] = []

        # language=xpath
        if node.find("fld[@na='eHircType']").attrib["va"] != MusicTrack.NodeTypeID:
            # language=
            raise HIRCParser.ParsingException("Not a MusicTrack Node")
        # language=xpath
        uid = node.find("fld[@na='ulID']").attrib["va"]
        super().__init__(uid)
        # language=xpath
        self.sectionSize = int(node.find("fld[@na='dwSectionSize']").attrib["vf"], 16)
        # language=xpath
        self.sourcesCount = int(node.find("obj[@na='MusicTrackInitialValues']/fld[@na='numSources']").attrib["va"])
        # language=xpath
        for elem in list(node.find("obj[@na='MusicTrackInitialValues']/lst[@na='pSource']")):
            elem = cast(Element, elem)
            # get id to collect the corresponding playlist element
            elem_id = elem.find("obj[@na='AkMediaInformation']/fld[@na='sourceID']").attrib["va"]
            src_info: Element = \
                list(filter(lambda x: x.find("fld[@na='sourceID']").attrib["va"] == elem_id,  # type: ignore
                            node.findall(f"obj[@na='MusicTrackInitialValues']/lst[@na='pPlaylist']/obj")))[0]
            self.sources.append(MusicTrackSource.from_node(elem, src_info))

        for elem in node.find("obj[@na='MusicTrackInitialValues']/lst[@na='pItems']"):
            elem = cast(Element, elem)
            automation = ClipAutomation(
                type=ClipAutomationType(int(elem.find("fld[@na='eAutoType']").attrib["va"])),
                points=list(map(
                    lambda x: GraphPoint(start=x.find("fld[@na='From']").attrib["va"],  # type: ignore
                                         end=x.find("fld[@na='To']").attrib["va"],  # type: ignore
                                         interpolation=Interpolation(
                                             int(x.find("fld[@na='Interp']").attrib["va"]))),  # type: ignore
                    elem.find("lst[@na='pArrayGraphPoints']")))
            )
            self.automations.append(automation)

        self.parent = PendingLink[HIRCNode](
            node.find("obj[@na='MusicTrackInitialValues']/obj[@na='NodeBaseParams']/fld[@na='DirectParentID']").attrib[
                "va"])

        # make this class referencable
        PendingLink.report_ready(self.id, self)


class MusicSegment(HIRCNode):
    __serialize__ = ["__all__"]
    NodeTypeID = str(0x0A)

    def __init__(self, node: Element):
        # language=xpath
        if node.find("fld[@na='eHircType']").attrib["va"] != MusicSegment.NodeTypeID:
            # language=
            raise HIRCParser.ParsingException("Not a MusicSegment Node")

        uid = node.find("fld[@na='ulID']").attrib["va"]
        super().__init__(uid)

        base_path = "obj[@na='MusicSegmentInitialValues']/obj[@na='MusicNodeParams']"
        self.grid_period = float(node.find(f"{base_path}/obj[@na='AkMeterInfo']/fld[@na='fGridPeriod']").attrib["va"])
        self.tempo = float(node.find(f"{base_path}/obj[@na='AkMeterInfo']/fld[@na='fTempo']").attrib["va"])

        # not sure what this is
        self.time_sig_beat_value = int(
            node.find(f"{base_path}/obj[@na='AkMeterInfo']/fld[@na='uTimeSigBeatValue']").attrib["va"])
        self.sig_num_beats_bar = int(node.find(f"{base_path}/obj[@na='AkMeterInfo']/fld[@na='uTimeSigNumBeatsBar']").attrib["va"])
        if self.time_sig_beat_value != self.sig_num_beats_bar or self.time_sig_beat_value != 4:
            print("[WARN] Bar is not 4/4, transitions may sound borked")

        if float(node.find(f"{base_path}/obj[@na='AkMeterInfo']/fld[@na='fGridOffset']").attrib["va"]) != 0:
            # let's not focus on that
            raise HIRCParser.ParsingException("Segment is offset!")

        self.duration = float(node.find("obj[@na='MusicSegmentInitialValues']/fld[@na='fDuration']").attrib["va"])

        self.children: List[PendingLink[MusicTrack]] = []
        for node_ in node.findall(f"{base_path}/obj[@na='Children']/fld[@na='ulChildID']"):
            self.children.append(PendingLink[MusicTrack](node_.attrib["va"]))

        self.markers: Dict[str, float] = {}

        for node_ in node.findall(
                "obj[@na='MusicSegmentInitialValues']/lst[@na='pArrayMarkers']/obj[@na='AkMusicMarkerWwise']"):
            self.markers[node_.find("fld[@na='id']").attrib["va"]] = float(
                node_.find("fld[@na='fPosition']").attrib["va"])

        self.parent = PendingLink[HIRCNode](
            node.find(f"{base_path}/obj[@na='NodeBaseParams']/fld[@na='DirectParentID']").attrib["va"])

        # make this class referencable
        PendingLink.report_ready(self.id, self)


@dataclass
class RanSeqPlaylistItem:
    __serialize__ = ["__all__"]
    playlistItemID: str
    type: RandomSequencePlaylistType
    loop: int
    loop_min: int
    loop_max: int
    weight: int
    is_using_weight: bool
    is_shuffle: bool
    SegmentID: Optional[PendingLink[MusicSegment]]
    playlists: Optional[List[RanSeqPlaylistItem]] = None

    @classmethod
    def from_node(cls, node: Element):
        instance = cls(
            node.find("fld[@na='playlistItemID']").attrib["va"],
            RandomSequencePlaylistType(int(node.find("fld[@na='eRSType']").attrib["va"])),
            int(node.find("fld[@na='Loop']").attrib["va"]),
            int(node.find("fld[@na='LoopMin']").attrib["va"]),
            int(node.find("fld[@na='LoopMax']").attrib["va"]),
            int(node.find("fld[@na='Weight']").attrib["va"]),
            node.find("fld[@na='bIsUsingWeight']").attrib["va"] == "1",
            node.find("fld[@na='bIsShuffle']").attrib["va"] == "1",
            PendingLink(node.find("fld[@na='SegmentID']").attrib["va"]),
        )

        instance.playlists = []

        for child in node.find("lst[@na='pPlayList']"):
            instance.playlists.append(cls.from_node(child))

        PendingLink.report_ready(instance.playlistItemID, instance)

        return instance


class RandomSequenceControl(HIRCNode):
    __serialize__ = ["__all__"]
    NodeTypeID = str(0x0D)

    def __init__(self, node: Element):
        # language=xpath
        if node.find("fld[@na='eHircType']").attrib["va"] != RandomSequenceControl.NodeTypeID:
            # language=
            raise HIRCParser.ParsingException("Not a RandomSequenceControl Node")

        uid = node.find("fld[@na='ulID']").attrib["va"]
        super().__init__(uid)
        music_node_params_path = \
            "obj[@na='MusicRanSeqCntrInitialValues']/obj[@na='MusicTransNodeParams']/obj[@na='MusicNodeParams']"

        self.grid_period = float(
            node.find(f"{music_node_params_path}/obj[@na='AkMeterInfo']/fld[@na='fGridPeriod']").attrib["va"])
        self.tempo = float(node.find(f"{music_node_params_path}/obj[@na='AkMeterInfo']/fld[@na='fTempo']").attrib["va"])

        # not sure what this is
        self.time_sig_beat_value = int(
            node.find(f"{music_node_params_path}/obj[@na='AkMeterInfo']/fld[@na='uTimeSigBeatValue']").attrib["va"])

        self.sig_num_beats_bar = int(
            node.find(f"{music_node_params_path}/obj[@na='AkMeterInfo']/fld[@na='uTimeSigNumBeatsBar']").attrib["va"])
        if self.time_sig_beat_value != self.sig_num_beats_bar or self.time_sig_beat_value != 4:
            print("[WARN] Bar is not 4/4, transitions may sound borked")

        self.rules: List[TransitionRule] = []
        for ruleNode in node.find(
                "obj[@na='MusicRanSeqCntrInitialValues']/obj[@na='MusicTransNodeParams']/lst[@na='pRules']"):
            self.rules.append(TransitionRule.from_node(ruleNode))

        self.playlists: List[RanSeqPlaylistItem] = []

        for playlistNode in node.find("obj[@na='MusicRanSeqCntrInitialValues']/lst[@na='pPlayList']"):
            self.playlists.append(RanSeqPlaylistItem.from_node(playlistNode))

        self.children: List[PendingLink[MusicSegment]] = []

        for node_ in node.findall(f"{music_node_params_path}/obj[@na='Children']/fld[@na='ulChildID']"):
            self.children.append(PendingLink[MusicSegment](node_.attrib["va"]))

        self.parent = PendingLink[HIRCNode](
            node.find(f"{music_node_params_path}/obj[@na='NodeBaseParams']/fld[@na='DirectParentID']").attrib["va"])

        # make this class referencable
        PendingLink.report_ready(self.id, self)


class StateNode(HIRCNode):
    __serialize__ = ["__all__"]
    NodeTypeID = str(0x01)

    def __init__(self, node: Element):
        # language=xpath
        if node.find("fld[@na='eHircType']").attrib["va"] != StateNode.NodeTypeID:
            # language=
            raise HIRCParser.ParsingException("Not a State Node")

        uid = node.find("fld[@na='ulStateID']").attrib["va"]
        super().__init__(uid)

        PendingLink.report_ready(self.id, self)


@dataclass
class MeterInfo:
    __serialize__ = ["__all__"]
    grid_period: float
    tempo: float
    sig_beat: int
    sig_num_beats_bar: int

    @classmethod
    def from_node(cls, node: Element):
        instance = cls(
            grid_period=float(node.find("fld[@na='fGridPeriod']").attrib["va"]),
            tempo=float(node.find("fld[@na='fTempo']").attrib["va"]),
            sig_beat=int(node.find("fld[@na='uTimeSigBeatValue']").attrib["va"]),
            sig_num_beats_bar=int(node.find("fld[@na='uTimeSigNumBeatsBar']").attrib["va"]),
        )
        if instance.sig_beat != instance.sig_num_beats_bar:
            print(f"[WARN] This bar is not 4/4, transitions may be borked {instance.sig_num_beats_bar}/{instance.sig_beat}")

        if float(node.find("fld[@na='fGridOffset']").attrib["va"]):
            raise HIRCParser.ParsingException("Offset grid!")

        return instance


@dataclass
class SwitchLabel:
    __serialize__ = ["__all__"]
    key: str
    label: str


@dataclass
class DecisionTreeNode:
    __serialize__ = ["__all__"]
    weight: int
    probability: int
    key: Optional[PendingLink[Any]] = None
    nodes: Optional[List[DecisionTreeNode]] = None
    audioNode: Optional[PendingLink[HIRCNode]] = None

    def collect_keys(self):
        result = [self.key]
        for node in self.nodes or []:
            result = [*result, *(node.collect_keys() or [])]
        return result

    def decide(self, key: str):
        def hand_off_decision_to_deeper_node() -> Optional[DecisionTreeNode]:
            self.nodes = cast(List[DecisionTreeNode], self.nodes)
            found = [node.decide(key) for node in self.nodes if node.decide(key)]
            found.sort(key=lambda x: x.weight)
            return found[-1] if len(found) > 0 else None

        if self.key and not self.key.is_ready:
            raise ReferenceError("PendingLink not ready yet!")

        if self.key and self.key.ref.key == key:
            if not self.nodes:
                return self
            deeper_desc = hand_off_decision_to_deeper_node()
            if not deeper_desc:
                return self
            return deeper_desc
        if not self.key and not self.nodes:
            raise Exception("Orphaned NOOP Node")
        if not self.nodes and self.key != key:
            return None
        return hand_off_decision_to_deeper_node()

    @classmethod
    def from_node(cls, node: Element):
        instance = cls(
            weight=int(node.find("fld[@na='uWeight']").attrib["va"]),
            probability=int(node.find("fld[@na='uProbability']").attrib["va"])
        )

        key = node.find("fld[@na='key']").attrib["va"]
        if key != "0":
            instance.key = PendingLink(key)

        audio_node_id = node.find("fld[@na='audioNodeId']")
        if audio_node_id is not None:
            instance.audioNode = PendingLink[HIRCNode](audio_node_id.attrib["va"])

        has_children = node.find("fld[@na='children.uCount']")
        if has_children is not None:
            instance.nodes = []
            for node in node.find("lst[@na='pNodes']"):
                # recursively build the decision tree
                instance.nodes.append(cls.from_node(node))

        return instance


class DecisionTreeRoot:
    __serialize__ = ["__all__"]

    def __init__(self, node: Element):
        self.nodes = []
        for node in node.find("lst[@na='pNodes']"):
            self.nodes.append(DecisionTreeNode.from_node(node))

    def collect_keys(self):
        result = []
        for node in self.nodes:
            result = [*result, *(node.collect_keys() or [])]
        return list(set(result))

    def decide(self, key: SwitchLabel):
        decisions = [node.decide(key.key) for node in self.nodes if node.decide(key.key)]
        decisions.sort(key=lambda x: x.weight)
        return decisions[-1]


class GroupType(Enum):
    Switch = 0x00


@dataclass
class MusicSwitchArgument:
    __serialize__ = ["__all__"]
    group_type: GroupType
    group_id: str
    group_name = "UNKNOWN_ARGUMENT_NAME"


class MusicSwitchNode(HIRCNode):
    __serialize__ = ["__all__"]
    NodeTypeID = str(0x0C)

    def __init__(self, node: Element):
        # language=xpath
        if node.find("fld[@na='eHircType']").attrib["va"] != MusicSwitchNode.NodeTypeID:
            # language=
            raise HIRCParser.ParsingException("Not a MusicSwitch Node")

        uid = node.find("fld[@na='ulID']").attrib["va"]
        super().__init__(uid)

        paths = {
            "MusicSwitchCntrInitialValues": "obj[@na='MusicSwitchCntrInitialValues']",
            "MusicTransNodeParams": "obj[@na='MusicSwitchCntrInitialValues']/obj[@na='MusicTransNodeParams']",
            "MusicNodeParams": "obj[@na='MusicSwitchCntrInitialValues']/obj[@na='MusicTransNodeParams']/obj[@na='Music"
                               "NodeParams']",
            "NodeBaseParams": "obj[@na='MusicSwitchCntrInitialValues']/obj[@na='MusicTransNodeParams']/obj[@na='Music"
                              "NodeParams']/obj[@na='NodeBaseParams']",
        }

        parent_id = node.find(f"{paths['NodeBaseParams']}/fld[@na='DirectParentID']").attrib["va"]
        self.parent = PendingLink[HIRCNode](parent_id) if parent_id != '0' else None

        self.override_bus = PendingLink[Any](
            node.find(f"{paths['NodeBaseParams']}/fld[@na='OverrideBusId']").attrib["va"])

        self.children: List[PendingLink[HIRCNode]] = []

        for node_ in node.findall(f"{paths['MusicNodeParams']}/obj[@na='Children']/fld[@na='ulChildID']"):
            self.children.append(PendingLink[HIRCNode](node_.attrib["va"]))

        self.rules: List[TransitionRule] = []

        self.arguments: List[MusicSwitchArgument] = []
        for argumentNode in node.find(f"{paths['MusicSwitchCntrInitialValues']}/obj[@na='Arguments']/lst[@na='pArguments']"):
            arg = MusicSwitchArgument(
                GroupType(int(argumentNode.find("fld[@na='eGroupType']").attrib["va"])),
                argumentNode.find("fld[@na='ulGroup']").attrib["va"]
            )
            if arg.group_id in KNOWN_SWITCH_ARGUMENT_NAMES:
                arg.group_name = KNOWN_SWITCH_ARGUMENT_NAMES[arg.group_id]
            self.arguments.append(arg)

        for node_ in node.find(f"{paths['MusicTransNodeParams']}/lst[@na='pRules']"):
            self.rules.append(TransitionRule.from_node(node_))

        self.meter_info = MeterInfo.from_node(node.find(f"{paths['MusicNodeParams']}/obj[@na='AkMeterInfo']"))

        self.decision_tree = DecisionTreeRoot(
            node.find(f"{paths['MusicSwitchCntrInitialValues']}/obj[@na='AkDecisionTree']"))

        PendingLink.report_ready(self.id, self)


@dataclass
class BankMeta:
    __serialize__ = ["__all__"]

    SoundBankID: str
    padding: int


class HIRCParser:
    __serialize__ = ["meta", "nodes"]

    class ParsingException(Exception):
        ...

    @staticmethod
    def unpack_node(elem: Element) -> Optional[HIRCNode]:
        if elem.attrib["na"] == "CAkMusicTrack":
            return MusicTrack(elem)
        elif elem.attrib["na"] == "CAkMusicSegment":
            return MusicSegment(elem)
        elif elem.attrib["na"] == "CAkMusicRanSeqCntr":
            return RandomSequenceControl(elem)
        elif elem.attrib["na"] == "CAkState":
            return StateNode(elem)
        elif elem.attrib["na"] == "CAkMusicSwitchCntr":
            return MusicSwitchNode(elem)
        return None

    def unpack_all_nodes(self):
        # language=xpath
        for elem in list(self.hirc_root.find("lst[@na='listLoadedItem']")):
            self.nodes.append(self.unpack_node(elem))

    def __init__(self, hirc_root: Element, meta: BankMeta):
        self.hirc_root: Element = hirc_root
        self.meta: BankMeta = meta
        self.nodes: List[HIRCNode] = []

        # test if this *might* even be in the format we are looking for
        if hirc_root.find("fld[@na='dwTag']").attrib["va"] != "b'HIRC'":
            raise self.ParsingException("Not a HIRC tree")


root = cast(Element, root)
parser = HIRCParser(
    # language=xpath
    root.find("base/root/obj[@na='HircChunk']"),
    BankMeta(
        # language=xpath
        SoundBankID=root.find(
            "base/root/obj[@na='BankHeader']/obj[@na='AkBankHeader']/fld[@na='dwSoundBankID']").attrib["va"],
        # language=xpath
        padding=int(
            root.find("base/root/obj[@na='BankHeader']/obj[@na='AkBankHeader']/fld[@na='padding']").attrib["vf"], 16),
    )
)

KNOWN_SWITCH_ARGUMENT_NAMES = {
    "2211399158": "ambient_music_switch"
}
def inject_supplemental_data():
    # collect all results and return them, so they won't get garbage-collected
    result: List[SwitchLabel | HIRCNode | Any] = []

    switch_labels = {
        "18883840": "light_action",
        "184709120": "action_dire",
        "209137191": "action",
        "529726532": "end",
        "782826392": "default",
        "1125500713": "intro",
        "1571361561": "tension",
        "2054095106": "high_action",
        "3207465375": "high_action_dire"
    }

    for key, label in switch_labels.items():
        instance = SwitchLabel(key, label)
        PendingLink.report_ready(key, instance)
        result.append(instance)

    return result


_keep = inject_supplemental_data()
parser.unpack_all_nodes()

print(parser.meta)

# test recursive decision tree resolve
#print(
#    list(filter(lambda x: type(x) == MusicSwitchNode, parser.nodes))[0].decision_tree.decide(_keep[0]))  # type: ignore
print(parser)


def dump_json(start: object):
    obj_index: Dict[str, Any] = {}

    def dump_json_inner(obj: object):
        # assume dicts are always serializable
        primitives = [int, float, str, bool, type(None), dict]

        if type(obj) in primitives:
            return obj

        d: Dict[str, Any] = {}
        props = []
        if hasattr(obj, "__serialize__"):
            props = getattr(obj, "__serialize__")
            if props[0] == "__all__":
                props = list(obj.__dict__.keys())

        if hasattr(obj, "__json__") and callable(getattr(obj, "__json__")):
            d = getattr(obj, "__json__")()

        if not d and not props:
            # handle enums
            if issubclass(type(obj), Enum):
                return type(obj).__name__ + "." + obj.name  # type: ignore
            raise Exception("Can't serialize " + repr(obj))

        if not d:
            for prop in props:
                value = getattr(obj, prop)
                if type(value) in primitives:
                    d[prop] = value
                elif type(value) == list:
                    if len(value) == 0:
                        d[prop] = []
                    else:
                        if type(value[0]) in primitives:
                            d[prop] = value
                        else:
                            d[prop] = []
                            for x in value:
                                # sort all hirc nodes in a separate index and link to them
                                if issubclass(type(x), HIRCNode):
                                    obj_index[x.id] = {**dump_json_inner(x), "_nodeType": type(x).__name__}
                                    d[prop].append({"refTo": x.id})
                                else:
                                    d[prop].append(dump_json_inner(x))
                else:
                    # sort all hirc nodes in a separate index and link to them
                    if issubclass(type(value), HIRCNode):
                        obj_index[value.id] = {**dump_json_inner(value), "_nodeType": type(value).__name__}
                        d[prop] = {"refTo": value.id}
                    else:
                        d[prop] = dump_json_inner(value)

        return d

    for aux in _keep:
        if hasattr(aux, "key"):
            obj_index[aux.key] = dump_json_inner(aux)

    params: List[PendingLink[SwitchLabel]] = []

    for switch in filter(lambda x: type(x) == MusicSwitchNode, parser.nodes):
        switch = cast(MusicSwitchNode, switch)
        params = [*params, *(switch.decision_tree.collect_keys() or [])]
    params = list(filter(bool, params))
    params = list(map(lambda x: x.__json__(), params))

    return {"start": dump_json_inner(start), "_index": obj_index, "params": params}


def convert_wem(source_id: str, in_dir: str, vgmstream_path: str):
    mp3 = io.BytesIO()
    print("Converting wem→wav ", source_id)
    proc = subprocess.Popen([vgmstream_path, "-p", str(Path(in_dir) / (source_id + ".wem"))], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = proc.communicate()
    print(err)
    print("Converting wav→mp3", source_id)
    pydub.AudioSegment.from_file(io.BytesIO(out), format="wav").export(mp3, format="ogg", bitrate="192k")
    return mp3


def create_bnkbdl(out: IO, hirc_parser: HIRCParser, in_dir=Path(__file__).parent.parent / "wem"):
    result = io.BytesIO()
    version = 1
    result.write(bytes(b"\xBB\xD0WWEBPLAYER\x13\x37"))
    # write version as an 8-bit uint
    result.write(version.to_bytes(1, "big", signed=False))
    raw_json = json.dumps(dump_json(parser))
    result.write(bytes(b"\00"))
    json_bytes = bytes(raw_json, "UTF8")

    counter = 0
    index = {"@main_json": [counter, len(json_bytes)]}
    counter += len(json_bytes)
    files: List[Tuple[str, io.BytesIO, int]] = []
    added: Set[str] = set()

    for track in filter(lambda x: type(x) == MusicTrack, hirc_parser.nodes):
        track = cast(MusicTrack, track)
        for source in track.sources:
            if source.sourceId in added:
                continue
            file = convert_wem(source.sourceId, str(in_dir), "/home/lea/vgmstream-cli")
            files.append((source.sourceId, file, file.getbuffer().nbytes))
            added.add(source.sourceId)

    for file in files:
        index[file[0]] = [counter, file[1].getbuffer().nbytes]
        counter += file[2]

    index_bytes = bytes(json.dumps(index), "UTF8")
    # write the index length as a 32-bit uint
    result.write(len(index_bytes).to_bytes(4, "big", signed=False))
    result.write(bytes(b"\00"))

    result.write(index_bytes)
    result.write(bytes(b"\x00"))
    files.insert(0, ("@main_json", io.BytesIO(json_bytes), len(json_bytes)))

    for file in files:
        result.write(file[1].read())

    result.write(bytes(b"\xED"))

    result.seek(0)
    out.write(result.read())


create_bnkbdl(open(main_args["out"], "wb"), parser)

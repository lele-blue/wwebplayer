import type {Writable} from "svelte/store";
import {writable} from "svelte/store";

export class HIRCNode {
    constructor(public id: string) {
    }
}

enum ClipAutomationType {
    Volume = "ClipAutomationType.Volume",
    FadeIn = "ClipAutomationType.FadeIn",
    FadeOut = "ClipAutomationType.FadeOut",
}

const linkRegistry = new Map<string, HIRCNode | any>()

export function registerNode(id: string, node: any) {
    linkRegistry.set(id, node)
}

export class PendingLink<T> {
    constructor(readonly refTo: string) {
    }

    get ref(): T {
        if (!linkRegistry.has(this.refTo)) {
            throw new Error(`Link ${this.refTo} not ready yet`)
        }
        return linkRegistry.get(this.refTo)
    }

    get is_ready(): boolean {
        return linkRegistry.has(this.refTo)
    }
}

enum Interpolation {
    Sine = 0x01,
    Log1 = 0x02,
    Linear = 0x04,
    SCurve = 0x05,
    Exp1 = 0x06,
    SineRecip = 0x07,
    Constant = 0x09
}

class GraphPoint {
    start: string // is a number
    end: string // is a number
    interpolation: Interpolation
}

class ClipAutomation {
    type: ClipAutomationType
    points: GraphPoint[]
}

export class MusicTrackSource {
    sourceId: string
    hasSource: boolean
    playAt: number
    trimOffsets: { start: number, end: number }
    duration: number
    file_reader: BnkBdlFileReader

    async get_blob(): Promise<Blob> {
        return this.file_reader.get_file(this.sourceId);
    }

    constructor(sourceId: string, hasSource: boolean, playAt: number, trimOffsets: { start: number; end: number }, duration: number, file_reader: BnkBdlFileReader) {
        this.sourceId = sourceId;
        this.hasSource = hasSource;
        this.playAt = playAt;
        this.trimOffsets = trimOffsets;
        this.duration = duration;
        this.file_reader = file_reader
    }
}

export type SerializedPendingLink = {
    refTo: string
}

export class MusicTrack extends HIRCNode {
    automations: ClipAutomation[]
    sectionSize: number
    sourcesCount: number
    sources: MusicTrackSource[]
    parent: PendingLink<MusicSegment>

    constructor(id: string, automations: ClipAutomation[], sectionSize: number, sourcesCount: number, sources: MusicTrackSource[], parent: SerializedPendingLink, file_reader: BnkBdlFileReader) {
        super(id);
        this.automations = automations;
        this.sectionSize = sectionSize;
        this.sourcesCount = sourcesCount;
        this.sources = [];
        for (const source of sources) {
            this.sources.push(new MusicTrackSource(source.sourceId, source.hasSource, source.playAt, source.trimOffsets, source.duration, file_reader))
        }
        this.parent = new PendingLink(parent.refTo);
        registerNode(id, this)
    }
}

class PrimedSegment {
    public readonly segment: MusicSegment;
    is_used: boolean = false;
    readonly #audio_buffers: Record<string, { audio: AudioBufferSourceNode, track: MusicTrack, source: MusicTrackSource, fadeNode: GainNode }> = {};


    constructor(segment: MusicSegment, audio_buffers: Record<string, { audio: AudioBufferSourceNode; track: MusicTrack; source: MusicTrackSource, fadeNode: GainNode }>, private ctx: AudioContext) {

        this.#audio_buffers = audio_buffers;
        this.segment = segment;
    }

    stop() {
        for (const source of Object.values(this.#audio_buffers)) {
            source.audio.stop();
        }
    }

    play(time_offset: number /*in Seconds*/) {
        if (this.is_used) {
            throw new Error("Double-Fire!")
        }
        this.is_used = true;
        for (const source of Object.values(this.#audio_buffers)) {
            // queue and apply automations
            if (source.track.automations) {
                for (let automation of source.track.automations) {
                    if ([ClipAutomationType.FadeIn, ClipAutomationType.FadeOut, /*ClipAutomationType.Volume*/].includes(automation.type)) {
                        let sortedPoints = automation.points.sort((a, b) => +a.start - +b.start);
                        setTimeout(() => {
                            source.fadeNode.gain.value = +sortedPoints[0].end;
                        }, Number.parseFloat(sortedPoints[0].start));
                        for (let i = 0; i < sortedPoints.length-1; i++){
                            const point = automation.points[i];
                            setTimeout(() => {
                                console.log("Fading " + automation.type + " to " + automation.points[i+1].end)
                                let fadeTo = +automation.points[i+1].end;
                                source.fadeNode.gain.exponentialRampToValueAtTime(fadeTo===0?0.00001:fadeTo, this.ctx.currentTime + time_offset + Number.parseFloat(automation.points[i+1].start) - Number.parseFloat(point.start))
                            }, Number.parseFloat(point.start))
                        }
                    } else {
                        console.warn("Unknown Automation " + automation.type, automation)
                    }
                }
            }
            if (Math.abs(source.source.playAt) !== Math.abs(source.source.trimOffsets.start)) {
                console.warn("TRIM OFFSETS DONT MATCH playAt. This is a desaster!")
            }
            let startOffset = 0 // (source.source.playAt + source.source.trimOffsets.start) / 1000;
            setTimeout(() => {
                console.log("Starting", source.source.sourceId, `(delayed by ${startOffset}s)`)
            }, startOffset * 1000)
            source.audio.start(this.ctx.currentTime + time_offset + startOffset, Math.abs(source.source.trimOffsets.start) / 1000);

            // handle ending
            if (source.source.trimOffsets.end < 0) {
                source.audio.stop(this.ctx.currentTime + time_offset + startOffset + (source.source.duration + source.source.trimOffsets.end - source.source.trimOffsets.start) / 1000);
                console.log(source.source.sourceId + " should end in " + ((source.source.duration + source.source.trimOffsets.end - source.source.trimOffsets.start) / 1000) + "s")
            } else if (source.source.trimOffsets.end !== 0) {
                console.warn("Positive Trim Offset End not supported, sound may overlap")
            }
            source.audio.addEventListener("ended", () => {
                console.log(source.source.sourceId + " ended")
            })
            if (source.source.trimOffsets.start < 0) {
                console.warn("Negative Trim Offset Start not implemented, here comes the bork…")
            }
        }
    }
}

export class MusicSegment extends HIRCNode {
    grid_period: number
    tempo: number
    time_sig_beat_value: number
    sig_num_beats_bar: number
    duration: number
    children: PendingLink<MusicTrack>[]
    markers: Record<string, number>
    parent: PendingLink<"RanSeq">


    constructor(id: string, grid_period: number, tempo: number, time_sig_beat_value: number, duration: number, children: SerializedPendingLink[], markers: Record<string, number>, parent: SerializedPendingLink, sig_num_beats_bar: number) {
        super(id);
        this.grid_period = grid_period;
        this.tempo = tempo;
        this.time_sig_beat_value = time_sig_beat_value;
        this.sig_num_beats_bar = sig_num_beats_bar;
        this.duration = duration;
        this.children = [];
        for (const child of children) {
            this.children.push(new PendingLink<MusicTrack>(child.refTo))
        }
        this.markers = markers;
        if (Object.values(this.markers).length !== 2 || !("43573010" in this.markers && "1539036744" in this.markers)) {
            console.warn("[WARN] Markers are not standard start-end markers", this.markers);
        }
        this.parent = new PendingLink(parent.refTo);

        registerNode(id, this)
    }

    async prime(ctx: AudioContext, destinationNode: AudioNode): Promise<PrimedSegment> {
        let blobs: Record<string, Promise<Blob>> = {}
        for (const child of this.children) {
            for (const source of child.ref.sources) {
                blobs[source.sourceId] = source.get_blob()
            }
        }

        await Promise.all(Object.values(blobs))
        let buffers = {}

        for (const child of this.children) {
            for (const source of child.ref.sources) {
                let buffer = await ctx.decodeAudioData(await (await blobs[source.sourceId]).arrayBuffer())
                let audio_source = ctx.createBufferSource();
                audio_source.buffer = buffer;
                const fadeNode = ctx.createGain();
                fadeNode.connect(destinationNode)
                audio_source.connect(fadeNode);
                buffers[source.sourceId] = {audio: audio_source, track: child.ref, source, fadeNode}
            }
        }

        return new PrimedSegment(this, buffers, ctx);
    }
}

export enum SyncType {
    Immediate = "SyncType.Immediate",
    NextGrid = "SyncType.NextGrid",
    NextBar = "SyncType.NextBar",
    NextMarker = "SyncType.NextMarker",
    ExitMarker = "SyncType.ExitMarker"
}

class TransitionSourceRule {
    time: number
    curve: Interpolation
    fade_offset: number
    sync_type: SyncType
}

export enum JumpToType {
    StartOfPlaylist = "JumpToType.StartOfPlaylist",
    // jump_to_id must be set for SpecificItem
    SpecificItem = "JumpToType.SpecificItem"
}

export enum TransitionDestinationEntryType {
    EntryMarker = "TransitionDestinationEntryType.EntryMarker",
    SameTime = "TransitionDestinationEntryType.SameTime",
}

class TransitionDestinationRule {
    time: number
    curve: Interpolation
    fade_offset: number
    jump_to_type: JumpToType
    jump_to?: PendingLink<RanSeqPlaylistItem>
    entry_type?: TransitionDestinationEntryType


    constructor(time: number, curve: Interpolation, fade_offset: number, jump_to_type: JumpToType, jump_to: SerializedPendingLink, entry_type?: TransitionDestinationEntryType) {
        this.time = time;
        this.curve = curve;
        this.fade_offset = fade_offset;
        this.jump_to_type = jump_to_type;
        this.jump_to = jump_to ? new PendingLink(jump_to.refTo) : undefined;
        this.entry_type = entry_type;
    }
}

class FadeParams {
    time: number
    curve: Interpolation
    fade_offset: number
}

class TransitionRule {
    source_rule: TransitionSourceRule
    destination_rule: TransitionDestinationRule
    is_noop: boolean
    source?: PendingLink<HIRCNode>
    destination?: PendingLink<HIRCNode>
    segment?: PendingLink<MusicSegment>
    segment_fade_in?: FadeParams
    segment_fade_out?: FadeParams


    constructor(source_rule: TransitionSourceRule, destination_rule: TransitionDestinationRule, is_noop: boolean, source: SerializedPendingLink, destination: SerializedPendingLink, segment: SerializedPendingLink, segment_fade_in: FadeParams, segment_fade_out: FadeParams) {
        this.source_rule = source_rule;
        this.destination_rule = new TransitionDestinationRule(destination_rule.time, destination_rule.curve, destination_rule.fade_offset, destination_rule.jump_to_type, destination_rule.jump_to as unknown as SerializedPendingLink, destination_rule.entry_type);
        this.is_noop = is_noop;
        this.source = source ? new PendingLink<HIRCNode>(source.refTo) : undefined;
        this.destination = destination ? new PendingLink<HIRCNode>(destination.refTo) : undefined;
        this.segment = segment ? new PendingLink<MusicSegment>(segment.refTo) : undefined;
        this.segment_fade_in = segment_fade_in;
        this.segment_fade_out = segment_fade_out;
    }
}

function exhaust_enum(item: never) {
    throw new Error("Unreachable");
}

export class RandomSequenceControl extends HIRCNode {
    grid_period: number
    tempo: number
    time_sig_beat_value: number
    sig_num_beats_bar: number
    rules: TransitionRule[]
    children: PendingLink<MusicSegment>[]
    parent: PendingLink<HIRCNode>
    playlists: RanSeqPlaylistItem[]
    private transitionInject: ((playIn: number) => void)[] = []

    addEventListener(type: "transitionInject", callback: (playIn: number) => void) {
        this.transitionInject.push(callback)
    }


    constructor(id: string, grid_period: number, tempo: number, time_sig_beat_value: number, rules: TransitionRule[], children: SerializedPendingLink[], parent: SerializedPendingLink, playlists: RanSeqPlaylistItem[], sig_num_beats_bar: number) {
        super(id);
        this.grid_period = grid_period;
        this.tempo = tempo;
        this.time_sig_beat_value = time_sig_beat_value;
        this.sig_num_beats_bar = sig_num_beats_bar;
        this.rules = [];
        for (const rule of rules) {
            this.rules.push(new TransitionRule(
                rule.source_rule, rule.destination_rule, rule.is_noop, rule.source as any, rule.destination as any, rule.segment as any, rule.segment_fade_in!, rule.segment_fade_out!
            ))
        }
        this.playlists = playlists.map(e => new RanSeqPlaylistItem(
            e.playlistItemID, e.type, e.loop, e.loop_min, e.loop_max, e.weight, e.is_using_weight, e.is_shuffle, e.SegmentID as any, e.playlists!
        ));
        if (this.playlists.length !== 1) {
            console.warn("Root Playlist not 1-Length")
        }
        this.children = [];
        for (const child of children) {
            this.children.push(new PendingLink<MusicSegment>(child.refTo))
        }
        this.parent = new PendingLink(parent.refTo);
        registerNode(id, this);
    }

    private primed_segments: PrimedSegment[] = [];

    async prime(ctx: AudioContext, destinationNode: AudioNode) {
        // add PrimedSegments, so we can be sure to be able to start every segment
        const missing = this.children.filter(c => !this.primed_segments.filter(x => !x.is_used).map(x => x.segment).includes(c.ref));
        this.primed_segments = [...this.primed_segments, ...await Promise.all(missing.map(x => x.ref.prime(ctx, destinationNode)))];
    }

    // borrowed from https://stackoverflow.com/a/6274381/6508769
    private static shuffled_array<T>(a: T[], random: () => number): T[] {
        a = [...a];
        for (let i = a.length - 1; i > 0; i--) {
            const j = Math.floor(random() * (i + 1));
            [a[i], a[j]] = [a[j], a[i]];
        }
        return a;
    }

    * _traverse_playlist(root: RanSeqPlaylistItem, random: Generator<number, void>, common_state = {}) {
        if (root.SegmentID?.is_ready) {
            throw new Error("The root should be a playlist tree branch, not a leaf")
        }
        while (true) {
            switch (root.type) {
                case RandomSequencePlaylistType.ContinuousSequence: {
                    for (const child of root.playlists!) {
                        if (child.type === RandomSequencePlaylistType.NoneType) {
                            yield child.SegmentID!.ref;
                        } else {
                            yield* this._traverse_playlist(child, random, common_state)
                        }
                    }
                    break;
                }
                case RandomSequencePlaylistType.StepSequence: {
                    let child;
                    let playCount = common_state[root.playlistItemID];
                    if (playCount && playCount !== root.playlists!.length - 2) {
                        child = root.playlists![playCount + 1];
                        common_state[root.playlistItemID] = playCount + 1;
                    } else {
                        child = root.playlists![0];
                        common_state[root.playlistItemID] = 0;
                    }
                    if (child.type === RandomSequencePlaylistType.NoneType) {
                        yield child.SegmentID.ref;
                    } else {
                        yield* this._traverse_playlist(child, random, common_state)
                    }
                    break;
                }
                case RandomSequencePlaylistType.ContinuousRandom: {
                    for (const child of RandomSequenceControl.shuffled_array(root.playlists!, () => random.next().value!)) {
                        if (child.type === RandomSequencePlaylistType.NoneType) {
                            yield child.SegmentID!.ref;
                        } else {
                            yield* this._traverse_playlist(child, random, common_state)
                        }
                    }
                    break;
                }
                case RandomSequencePlaylistType.StepRandom: {
                    let child = root.playlists![Math.floor(random.next().value! * root.playlists!.length)];
                    if (child.type === RandomSequencePlaylistType.NoneType) {
                        yield child.SegmentID!.ref;
                    } else {
                        yield* this._traverse_playlist(child, random, common_state)
                    }
                    break;
                }
                case RandomSequencePlaylistType.NoneType: {
                    throw new Error("Is Leaf.");
                }
                default: {
                    exhaust_enum(root.type);
                }
            }
            if (!root.loop) {
                console.log("Loop finished for", root, "should break?")
            }
            break;
        }
    }

    * random(seed: number) {
        let state;

        function mul32() {
            state = seed += 0x6D2B79F5;
            state = Math.imul(state ^ state >>> 15, state | 1);
            state ^= state + Math.imul(state ^ state >>> 7, state | 61);
            return ((state ^ state >>> 14) >>> 0) / 4294967296;
        }

        while (true) {
            console.log("[RandomState] " + state)
            yield mul32()
        }
    }

    readonly current_segment: Writable<MusicSegment[]> = writable([]);
    private playing = true;
    get public_is_playing () {
        return this.playing
    }

    stop() {
        this.playing = false;
    }

    stop_immediately() {
        this.stop();
        for (const primedSegment of this.primed_segments.filter(x => x.is_used)) {
            primedSegment.stop();
        }
    }

    getRandomInt(random: Generator<number>, min: number, max: number) {
        min = Math.ceil(min);
        max = Math.floor(max);
        return Math.floor(random.next().value * (max - min + 1)) + min;
    }

    async play(ctx: AudioContext, destinationNode: AudioNode, seed: number = 0xF42A1EE7C001, override_first?: MusicSegment) {
        this.playing = true;
        const random = this.random(seed);
        const random2 = this.random(seed);
        let playlist = this._traverse_playlist(this.playlists[0], random);
        let playlist2 = this._traverse_playlist(this.playlists[0], random2);
        playlist2.next(); // let 2 be one item ahead
        if (override_first) {
            let i = 0;
            for (const e of playlist) {
                playlist2.next();
                i++;
                if (i === 1000) throw new Error("Item not in Playlist");
                if (e === override_first) break;
            }
        }

        let targetTimeNext = ctx.currentTime;
        let is_first = true;

        while (this.playing) {
            let child: MusicSegment;
            let next_child: MusicSegment;
            if (override_first) {
                child = override_first;
                next_child = playlist2.next().value; // let's just hope that p2 is not empty for now
                override_first = undefined;
            } else {
                const next = playlist.next();
                const next_next = playlist2.next();
                if (next.done) {
                    console.log("Regenerating Playlist")
                    playlist = this._traverse_playlist(this.playlists[0], random);
                    child = playlist.next().value;
                } else {
                    child = next.value;
                }
                if (next_next.done) {
                    playlist2 = this._traverse_playlist(this.playlists[0], random2);
                    next_child = playlist2.next().value;
                }
                else {
                    next_child = next_next.value;
                }
            }
            console.log("Playing", child, "next", next_child)
            let timingError = ctx.currentTime - targetTimeNext;
            console.log(`Set Timeout produced an error of ${timingError}S, correcting…`);
            this.primed_segments.find(x => x.segment === child && !x.is_used)!.play(1 - timingError);

            let beatCount = 0
            const barInterval = setInterval(() => {
                beatCount++;
                if (beatCount === child.time_sig_beat_value) {
                    beatCount = 0;
                    // todo dispatch bar listeners
                }
                // todo dispatch beat listeners
            }, 1 / (child.tempo / 60) * 1000);
            setTimeout(() => clearInterval(barInterval), child.duration)

            this.prime(ctx, destinationNode).then(() => {
            });

            this.current_segment.update(v => [...v, child])
            setTimeout(() => {
                this.current_segment.set([child]);
            }, child.markers["43573010"]);

            let timeoutDuration = child.markers["1539036744"] - next_child.markers["43573010"];

            console.log("DURATION: ", timeoutDuration)
            targetTimeNext = ctx.currentTime + timeoutDuration / 1000;

            const listenerInterval = setInterval(() => {
                this.transitionInject.map(e => e((targetTimeNext - ctx.currentTime) * 1000 + next_child.markers["43573010"]));
                this.transitionInject = [];
            }, 100);

            // wait for the duration of the inner part, meaning the end will play over into the next segment, and the start of the next segment starts during this segment
            await new Promise(resolve => setTimeout(resolve, timeoutDuration));

            clearInterval(listenerInterval);

            this.transitionInject.map(e => e(0)); // emergency-fire late added listeners, since the loop is likely already stopped
            // listeners are one-time only
            this.transitionInject = [];
        }
    }
}


class MeterInfo {
    grid_period: number;
    tempo: number;
    sig_beat: number;
    sig_num_beats_bar: number;
}

enum RandomSequencePlaylistType {
    NoneType = "RandomSequencePlaylistType.NoneType",
    ContinuousSequence = "RandomSequencePlaylistType.ContinuousSequence",
    StepSequence = "RandomSequencePlaylistType.StepSequence",
    ContinuousRandom = "RandomSequencePlaylistType.ContinuousRandom",
    StepRandom = "RandomSequencePlaylistType.StepRandom",
}

class RanSeqPlaylistItem {
    playlistItemID: string
    type: RandomSequencePlaylistType
    loop: number
    loop_min: number
    loop_max: number
    weight: number
    is_using_weight: boolean
    is_shuffle: boolean
    SegmentID?: PendingLink<MusicSegment>
    playlists?: RanSeqPlaylistItem[]


    constructor(playlistItemID: string, type: RandomSequencePlaylistType, loop: number, loop_min: number, loop_max: number, weight: number, is_using_weight: boolean, is_shuffle: boolean, SegmentID: SerializedPendingLink, playlists: RanSeqPlaylistItem[]) {
        this.playlistItemID = playlistItemID;
        this.type = type;
        this.loop = loop;
        this.loop_min = loop_min;
        this.loop_max = loop_max;
        this.weight = weight;
        this.is_using_weight = is_using_weight;
        this.is_shuffle = is_shuffle;
        this.SegmentID = new PendingLink<MusicSegment>(SegmentID.refTo);
        this.playlists = playlists.map(e => new RanSeqPlaylistItem(
            e.playlistItemID, e.type, e.loop, e.loop_min, e.loop_max, e.weight, e.is_using_weight, e.is_shuffle, e.SegmentID as any, e.playlists!
        ));
        registerNode(playlistItemID, this);

        if (SegmentID.refTo !== "0" && this.playlists.length) {
            throw new Error("Playlist item is playlist and item at the same time")
        }
    }
}

class DecisionTreeNode {
    weight: number
    probability: number
    key?: PendingLink<SwitchLabel>
    nodes?: DecisionTreeNode[]
    audioNode?: PendingLink<RandomSequenceControl>;


    decide(key: string) {
        const hand_off_decision_to_deeper_node = () => {
            let found: DecisionTreeNode[] = []
            for (const node of this.nodes!) {
                if (node.decide(key)) {
                    found.push(node.decide(key)!)
                }
            }
            found = found.sort((a, b) => a.weight - b.weight)
            return found.length > 0 ? found[found.length - 1] : null
        }

        if (this.key && !this.key.is_ready) {
            return null;
        }

        if (this.key && this.key.ref.key === key) {
            if (!this.nodes) {
                return this
            }
            const deeper_desc = hand_off_decision_to_deeper_node()
            if (!deeper_desc) {
                return this
            }
            return deeper_desc;
        }
        if (!this.key && !this.nodes) {
            console.warn("Orphaned NOOP Node");
            return null;
        }
        if (!this.nodes && this.key?.ref.key !== key) {
            return null
        }
        return hand_off_decision_to_deeper_node()
    }


    constructor(weight: number, probability: number, key?: SerializedPendingLink, nodes?: DecisionTreeNode[], audioNode?: SerializedPendingLink) {
        this.weight = weight;
        this.probability = probability;
        this.key = key ? new PendingLink(key.refTo) : undefined;
        this.audioNode = audioNode ? new PendingLink(audioNode.refTo) : undefined;
        if (nodes) {
            this.nodes = [];
            for (const node of nodes) {
                this.nodes.push(new DecisionTreeNode(
                    node.weight,
                    node.probability,
                    node.key as any,
                    node.nodes,
                    node.audioNode as any
                ))
            }
        }
    }
}

export class SwitchLabel {
    label: string
    key: string


    constructor(label: string, key: string) {
        this.label = label;
        this.key = key;
        registerNode(this.key, this);
    }
}

class DecisionTreeRoot {
    nodes: DecisionTreeNode[]


    constructor(nodes: DecisionTreeNode[]) {
        this.nodes = [];
        for (const node of nodes) {
            this.nodes.push(new DecisionTreeNode(
                node.weight,
                node.probability,
                node.key as unknown as SerializedPendingLink,
                node.nodes,
                node.audioNode as unknown as SerializedPendingLink
            ))
        }
    }

    decide(key: SwitchLabel) {
        let decisions: DecisionTreeNode[] = []
        for (const node of this.nodes) {
            if (node.decide(key.key)) {
                decisions.push(node.decide(key.key)!)
            }
        }
        decisions.sort((a, b) => a.weight - b.weight)
        return decisions[decisions.length - 1]
    }
}

export enum GroupType {
    Switch = "GroupType.Switch",
}

export class MusicSwitchArgument {
    group_type: GroupType;
    group_id: string;
    group_name: string;


    constructor(group_type: GroupType, group_id: string, group_name: string) {
        this.group_type = group_type;
        this.group_id = group_id;
        this.group_name = group_name;

        registerNode(group_id, this);
    }
}

export class MusicSwitchNode extends HIRCNode {
    parent?: PendingLink<unknown>;
    override_bus: PendingLink<never>;
    children: PendingLink<MusicSegment>[];
    rules: TransitionRule[];
    meter_info: MeterInfo;
    decision_tree: DecisionTreeRoot;
    arguments: MusicSwitchArgument[];
    private playing: RandomSequenceControl | null = null;
    now_playing = writable<null | SwitchLabel>(null);
    in_transition = writable<null | SwitchLabel>(null);
    get playing_rseq () {return this.playing}

    get is_noop() {
        return this.decision_tree.nodes.every(node => !node.key && !node.nodes)
    }

    get_switch_labels() {
        let result: PendingLink<SwitchLabel>[] = [];

        function inner(node: DecisionTreeNode) {
            if (node.key) {
                result.push(node.key);
            }
            if (node.nodes?.length) {
                for (const node_ of node.nodes) {
                    inner(node_);
                }
            }
        }

        for (const node of this.decision_tree.nodes) {
            inner(node)
        }

        return result.map(e => e.is_ready ? e.ref : {label: e.refTo, key: e.refTo});
    }

    async stop_gracefully(ctx: AudioContext, stop_label: SwitchLabel, destinationNode: AudioNode) {
        await this.transition_to_label(stop_label, ctx, destinationNode);
        this.playing?.stop();
        await new Promise<void>(resolve => this.playing?.addEventListener("transitionInject", stopIn => {
            setTimeout(resolve, stopIn);
        }));
        this.now_playing.set(null);
        this.playing = null;
    }

    async stop_immediately() {
        this.playing?.stop_immediately();
        this.now_playing.set(null);
        this.playing = null;
        this.in_transition.set(null);
    }

    async play_by_label(label: SwitchLabel, ctx: AudioContext, destinationNode: AudioNode) {
        const random_seq = this.decision_tree.decide(label).audioNode!.ref;
        await random_seq.prime(ctx, destinationNode);
        random_seq.play(ctx, destinationNode).then(() => {
        });
        this.playing = random_seq;
        this.now_playing.set(label);
    }

    get_transition_to(label: SwitchLabel): TransitionRule | null | undefined {
        let decision = this.decision_tree.decide(label);
        if (!decision?.audioNode?.is_ready) {
            console.warn("Decision could be made, but the random sequence is missing, disabling transition…");
            return undefined;
        }
        const target_rseq = decision.audioNode!.ref;
        const rules = this.rules.filter(r => r.source && r.source.is_ready && r.destination && r.destination.is_ready &&
            r.source?.ref === this.playing && r.destination?.ref == target_rseq);
        if (!rules.length) return null;
        return rules[0];

    }

    can_transition_to(label: SwitchLabel): boolean {
        if (!this.playing) {
            return this.get_transition_to(label) !== undefined;
        }
        return this.get_transition_to(label) !== null
    }

    async transition_to_label(label: SwitchLabel, ctx: AudioContext, destinationNode: AudioNode) {
        this.in_transition.set(label)
        const target_rseq = this.decision_tree.decide(label).audioNode!.ref;
        const rules = this.rules.filter(r => r.source && r.source.is_ready && r.destination && r.destination.is_ready &&
            r.source?.ref === this.playing && r.destination?.ref == target_rseq);
        const rule = rules[0];
        if (!rule) throw new Error("No Rule found, aborting…");
        console.log(rule);
        await target_rseq.prime(ctx, destinationNode);
        if (rule.segment) {
            const primedTransition = await rule.segment.ref.prime(ctx, destinationNode);
            this.playing!.stop();
            let resolve = (..._params: any[]) => {
            }
            console.log("adding injection listener")

            // this will fire 1s before we can start the transition, so we have 1s to load everything up
            this.playing?.addEventListener("transitionInject", playIn => {
                if (!this.playing) return;
                primedTransition.play(1 + playIn / 1000 - rule.segment!.ref.markers["43573010"] / 1000);
                setTimeout(() => {
                    console.log("going")
                    resolve();
                }, playIn-1)
            });
            await new Promise(resolve1 => resolve = resolve1);
            await new Promise(resolve => setTimeout(resolve, rule.segment!.ref.markers["1539036744"] - rule.segment!.ref.markers["43573010"]));
        } else {
            this.playing!.stop();
            await new Promise<void>(resolve => {
                this.playing!.addEventListener("transitionInject", playIn => {
                    setTimeout(() => {
                        console.log("going")
                        resolve();
                    }, playIn-1)
                });
            })
        }
        console.log("Transition ended")

        // in case a stop was issued mid-transition
        if (!this.playing) return;

        this.playing = target_rseq;
        this.now_playing.set(label);
        this.in_transition.set(null);
        if (rule.destination_rule.jump_to_type === JumpToType.StartOfPlaylist) {
            target_rseq.play(ctx, destinationNode).then(() => {
            });
        } else if (rule.destination_rule.jump_to_type === JumpToType.SpecificItem) {
            let first = rule.destination_rule.jump_to?.ref.SegmentID?.ref;
            target_rseq.play(ctx, destinationNode, 0xF42A1EE7C001, first).then(() => {
            });
        } else {
            throw new Error("JumpType Wrong")
        }
    }


    constructor(id: string, parent: SerializedPendingLink | undefined, override_bus: SerializedPendingLink, children: SerializedPendingLink[], rules: TransitionRule[], meter_info: MeterInfo, decision_tree: DecisionTreeRoot, arguments_: MusicSwitchArgument[]) {
        super(id);
        this.parent = parent ? new PendingLink(parent.refTo) : undefined;
        this.override_bus = new PendingLink(override_bus.refTo);
        this.children = [];
        for (const child of children) {
            this.children.push(new PendingLink(child.refTo))
        }
        this.rules = [];
        for (const rule of rules) {
            this.rules.push(new TransitionRule(
                rule.source_rule,
                rule.destination_rule,
                rule.is_noop,
                rule.source as unknown as SerializedPendingLink,
                rule.destination as unknown as SerializedPendingLink,
                rule.segment as unknown as SerializedPendingLink,
                rule.segment_fade_in!,
                rule.segment_fade_out!
            ))
        }
        this.meter_info = meter_info;
        this.decision_tree = new DecisionTreeRoot(decision_tree.nodes);
        if (arguments_) {
            this.arguments = arguments_.map(a => new MusicSwitchArgument(a.group_type, a.group_id, a.group_name))
        }
    }
}

export class BnkBdlFileReader {
    private data: Blob
    private index: Record<string, [number, number]>
    private data_offset: number


    constructor(data: Blob) {
        this.data = data;
    }

    async validate() {
        const buf = await new Response(this.data.slice(0, 0x15)).arrayBuffer();
        const view = new DataView(buf);
        if (
            view.getBigUint64(0, false) !== BigInt("0xbbd057574542504c") ||
            view.getUint32(8, false) !== 0x41594552 ||
            view.getUint16(12, false) !== 0x1337 ||
            view.getUint8(0xF) !== 0 ||
            view.getUint8(0x14) !== 0
        ) {
            throw new Error("Wrong Format")
        }
        const version = view.getUint8(0xE);
        const index_length = view.getUint32(0x10, false);
        console.log(version, index_length)
        this.index = await (new Response(this.data.slice(0x15, 0x15 + index_length)).json());
        this.data_offset = 0x15 + index_length + 1
    }

    get_file(id: string): Blob {
        const [start, length] = this.index[id]
        return this.data.slice(this.data_offset + start, this.data_offset + start + length)
    }

    async get_main_json() {
        return await new Response(this.get_file("@main_json")).json()
    }
}

// @ts-ignore
export function construct_from_json(manifest: any, file_reader: BnkBdlFileReader) {
    let tracks: MusicTrack[] = []
    for (const track_json of Object.values(manifest._index).filter((x: any) => x._nodeType === "MusicTrack") as MusicTrack[]) {
        tracks.push(new MusicTrack(track_json.id, track_json.automations, track_json.sectionSize, track_json.sourcesCount, track_json.sources, track_json.parent as any, file_reader))
    }


    let sequences: MusicSegment[] = []
    for (const seq_json of Object.values(manifest._index).filter((x: any) => x._nodeType === "MusicSegment") as MusicSegment[]) {
        sequences.push(new MusicSegment(seq_json.id, seq_json.grid_period, seq_json.tempo, seq_json.time_sig_beat_value, seq_json.duration, seq_json.children as any, seq_json.markers, seq_json.parent as any, seq_json.sig_num_beats_bar))
    }


    let ran_sequences: RandomSequenceControl[] = []
    for (const ran_json of Object.values(manifest._index).filter((x: any) => x._nodeType === "RandomSequenceControl") as RandomSequenceControl[]) {
        ran_sequences.push(new RandomSequenceControl(
            ran_json.id, ran_json.grid_period, ran_json.tempo, ran_json.time_sig_beat_value, ran_json.rules, ran_json.children as any, ran_json.parent as any, ran_json.playlists, ran_json.sig_num_beats_bar
        ))
    }

    let sw_nodes: MusicSwitchNode[] = []
    for (const sw_node of Object.values(manifest._index).filter((x: any) => x._nodeType === "MusicSwitchNode") as MusicSwitchNode[]) {
        let musicSwitchNode = new MusicSwitchNode(
            sw_node.id, sw_node.parent as any, sw_node.override_bus as any, sw_node.children as any, sw_node.rules, sw_node.meter_info, sw_node.decision_tree, sw_node.arguments
        );
        if (!musicSwitchNode.is_noop) {
            sw_nodes.push(musicSwitchNode);
        }
    }
    return {tracks, sequences, ran_sequences, sw_nodes}
}//
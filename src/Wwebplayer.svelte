<script lang="ts">
    import {
        BnkBdlFileReader, construct_from_json,
        MusicSegment,
        MusicSwitchNode,
        MusicTrack, PendingLink,
        RandomSequenceControl,
        SwitchLabel
    } from "./lib/HIRCNodes";
    import {get} from "svelte/store";
    import {createEventDispatcher, onDestroy, tick} from "svelte";
    import {SyncType, TransitionDestinationEntryType} from "./lib/HIRCNodes.js";

    export let manifest: { _index: any[] } = {};
    export let file_reader: BnkBdlFileReader;

    export let debug_segments = false;
    export let debug_ran_seqs = false;

    export let volume = 1;
    export let show_volume_slider = true;

    let dispatch = createEventDispatcher();
    $: {
        if (gainNode) {
            gainNode.gain.value = volume;
            dispatch("volumeChange", {volume});
        }
    }

    export let stop_on_destroy = false;

    onDestroy(() => {
        if (stop_on_destroy) {
            sw_nodes[0].stop_immediately();
            dispatch("stop_immediately")
        }
    })

    export let sw_nodes: MusicSwitchNode[];

    let tracks = [];
    let sequences = [];
    let ran_sequences: RandomSequenceControl[] = []


    if (!sw_nodes) {
        ({tracks, sequences, ran_sequences, sw_nodes} = construct_from_json(manifest, file_reader))
    } else {
        tick().then(() => {
            prev_active_switch = get(sw_nodes[0].now_playing);
            active_switch = get(sw_nodes[0].now_playing);
        })
    }


    console.log(sw_nodes)

    async function play_segment(seq: MusicSegment) {
        console.log(seq)
        const ctx = new AudioContext();
        const gain = ctx.createGain();
        gain.connect(ctx.destination);
        (await seq.prime(ctx, gain)).play(0)
    }

    async function play_ranseq(seq: RandomSequenceControl) {
        const ctx = new AudioContext();
        const gain = ctx.createGain();
        gain.connect(ctx.destination);
        await seq.prime(ctx, gain);
        await seq.play(ctx, gain);
    }

    let labels = {}
    const raw_switch_labels: Record<string, string> = {}

    for (const ref of (<{ params: { refTo: string }[] }>manifest).params) {
        if (manifest._index[ref.refTo]) {
            raw_switch_labels[ref.refTo] = manifest._index[ref.refTo].label;
        } else {
            raw_switch_labels[ref.refTo] = ref.refTo;
        }
    }

    for (const [key, label] of Object.entries(raw_switch_labels)) {
        labels[label] = new SwitchLabel(label, key);
    }

    const stop_label = new SwitchLabel("end", "529726532");

    let current_sequences = {};
    for (const [i, seq] of ran_sequences.entries()) {
        seq.current_segment.subscribe(v => {
            current_sequences[i] = v;
        })
    }

    let active_switch: null | SwitchLabel = null;
    let prev_active_switch = null;

    export let active_sw_node = 0;

    $: in_transition = sw_nodes[active_sw_node].in_transition;
    $: label_active = sw_nodes[active_sw_node].now_playing;

    export let ctx: AudioContext | null = null;
    export let gainNode: GainNode | null = null;

    function createAudioContext() {
        if (!ctx) {
            ctx = new AudioContext();
            gainNode = ctx.createGain();
            gainNode.connect(ctx.destination);
        }
    }


    $: {
        if (active_switch && !prev_active_switch) {
            createAudioContext();
            sw_nodes[active_sw_node].play_by_label(active_switch, ctx!, gainNode!);
            prev_active_switch = active_switch;
            dispatch("start_play", {switch: active_switch});
        } else if (active_switch && prev_active_switch && prev_active_switch !== active_switch) {
            sw_nodes[active_sw_node].transition_to_label(active_switch, ctx!, gainNode!).then(() => {
                prev_active_switch = active_switch;
            });
            dispatch("transition", {switch: active_switch})
        }
    }

</script>

<style>
    .active {
        color: pink;
    }

    .transitioning {
        animation: transition_going 1s linear infinite;
    }

    .disabled {
        background: red;
    }

    .segmentedTransition {
        background: yellow;
    }

    @keyframes transition_going {
        0% {
            background: pink;
        }
        49% {
            background: pink;
        }
        50% {
            background: inherit;
        }
        100% {
            background: inherit;
        }
    }
</style>

<main>
    {#if debug_segments}
        {#each sequences as seq, i}
            <button on:click={() => play_segment(seq)}>Go #{i}</button>
        {/each}
        <br/>
    {/if}
    {#if debug_ran_seqs}
        {#each ran_sequences as r_seq, i}
            {r_seq.id}
            <button on:click={() => play_ranseq(r_seq)}>ranseq</button>
            {#each r_seq.children.map(x => x.ref) as seq}
                <button class:active={(current_sequences[i] ?? []).includes(seq)}
                        on:click={() => play_segment(seq)}>{seq.id}</button>
            {/each}
            <br/>
        {/each}
    {/if}

    {#each sw_nodes as sw_node, i}
        {sw_node.arguments?.map(e => e.group_name).join(", ") ?? "Unknown Switch"}
        {#each sw_node.get_switch_labels() as obj}
            <button class:disabled={!(sw_node.can_transition_to(obj, $label_active)) || ($label_active && i !== active_sw_node)}
                    class:transitioning={$in_transition?.key === obj.key && i === active_sw_node} class:active={$label_active?.key === obj.key && i === active_sw_node}
                    on:click={() => {active_sw_node = i; active_switch = obj}}>
                {obj.label}
                {#if sw_node.get_transition_to(obj, $label_active)?.segment}
                    [S]
                {/if}
                {#if sw_node.get_transition_to(obj, $label_active)?.destination_rule.entry_type === TransitionDestinationEntryType.SameTime}
                    [ST]
                {/if}
                {#if sw_node.get_transition_to(obj, $label_active)?.source_rule.sync_type === SyncType.Immediate}
                    [IMM]
                {/if}
            </button>
        {/each}
        <br/><br/>
    {/each}
    <br/>
    <button class:transitioning={$in_transition?.key === stop_label.key}
            class:disabled={!(sw_nodes[active_sw_node].can_transition_to(stop_label, $label_active))}
            on:click={() => {dispatch("stop"); sw_nodes[active_sw_node].stop_gracefully(ctx, stop_label, gainNode); active_switch = null; prev_active_switch=null;}}>
        Stop
        {#if sw_nodes[active_sw_node].get_transition_to(stop_label, $label_active)?.segment}
            [S]
        {/if}
    </button>
    <button on:click={() => {dispatch("stop_immediately"); sw_nodes.forEach(e => e.stop_immediately()); active_switch = null; prev_active_switch=null;}}>
        Stop NOW
    </button>
    {#if show_volume_slider}
        <input type="range" min="0" max="1" step="0.01" bind:value={volume}/>
    {/if}
</main>

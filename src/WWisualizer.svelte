<script lang="ts">
    import {MusicSegment, RandomSequenceControl} from "./lib/HIRCNodes";
    import {onDestroy} from "svelte";

    export let randomSequence: RandomSequenceControl;
    export let ctx: AudioContext;

    let gen_length: number[] = [];

    function* cycle_generator<T>(gen_gen: () => Generator<T>): Generator<T> {
        let cycle = 0;
        while (true) {
            let counter = 0;
            for (const i of gen_gen()) {
                counter++;
                yield i;
            }
            gen_length[cycle] = counter;
            cycle++;
        }
    }

    let playlist: MusicSegment[] = [];

    let startTime = 0;

    if (randomSequence.public_is_playing) {
        startTime = ctx.currentTime;
    }

    let _i = 0;
    console.log(randomSequence._traverse_playlist)
    let random = randomSequence.random(0xF42A1EE7C001);
    for (const item of cycle_generator(() => randomSequence._traverse_playlist(randomSequence.playlists[0], random))) {
        _i++;
        if (_i === 100) break;
        playlist.push(item);
    }

    let scaling = 0.002;

    let currentEnd = playlist[0].markers["43573010"] * scaling;

    function get_markers(item: MusicSegment) {
        return item.markers
    }

    let left_cache = {}

    function get_left(item, id) {
        if (id in left_cache) return left_cache[id];
        let r = currentEnd - get_markers(item)["43573010"] * scaling;
        currentEnd += (get_markers(item)["1539036744"] - get_markers(item)["43573010"]) * scaling;
        left_cache[id] = r;
        return r
    }

    const interval = setInterval(() => {
        ctx = ctx;
    }, 100);
    onDestroy(() => clearInterval(interval));


    function get_item_color(index: number) {
        let acc = 0;
        for (let i = 0; i < gen_length.length; i++) {
            const count = gen_length[i];
            if (acc <= index && acc + count > index) {
                return ["#747bff", "#b34cc2"][i % 2]
            }
            acc += count;
        }
        return "yellow"
    }
</script>

<style>
    .item:hover, .track:hover {
        z-index: 2;
        border: 1px solid black
    }
</style>

<div style="overflow: auto; position: relative; height: 1000px">
    {#each playlist as item, i}
        <div class="item" style:top={i*30 + "px"} style:left={get_left(item, i) + "px"}
             style:width={item.duration*scaling + "px"}
             style:background={get_item_color(i)}
             style="height: 100px; position: absolute; border: 1px solid green"
             on:click={() => console.log(item)}
        >
            <div style="position: relative; width: 100%; height: 100%">
                <span>{item.id} ({i})</span>
                <div style:left={item.markers["43573010"] * scaling + "px"}
                     style="top: 0; position: absolute; height: 100px; background: darkolivegreen; width: 3px;"></div>
                <div style:left={item.markers["1539036744"] * scaling + "px"}
                     style="top: 0; position: absolute; height: 100px; background: indianred; width: 3px;"></div>
            </div>
        </div>
        {#each item.children.map(x => x.ref.sources).flat() as child, u}
            <div class="track" style:width={child.duration * scaling + "px"}
                 style:left={get_left(item, i) - Math.abs(child.playAt*scaling) + "px"}
                 style:top={i*30+100+(u)*20 + "px"}
                 style="height: 20px; background: coral; border-radius: 4px; position: absolute"
                 on:click={() => console.log(child)}
            >
                <div style="position:relative; width: 100%; height: 100%">
                    <div>{child.sourceId}</div>
                    <div style:left={child.trimOffsets.start * scaling + "px"}
                         style="top: 0; position: absolute; height: 20px; background: greenyellow; width: 3px;"></div>
                    {#if child.trimOffsets.end > 0}
                        <div style:left={child.trimOffsets.end * scaling + "px"}
                             style="top: 0; position: absolute; height: 20px; background: darkred; width: 3px;"></div>
                    {:else if child.trimOffsets.end === 0}
                        <div style="left: 99%; top: 0; position: absolute; height: 20px; background: darkred; width: 3px;"></div>
                    {:else if child.trimOffsets.end < 0}
                        <div style:left={(child.duration + child.trimOffsets.end) * scaling + "px"}
                             style="top: 0; position: absolute; height: 20px; background: darkred; width: 3px;"></div>
                    {/if}
                </div>
            </div>
        {/each}
    {/each}
    <div style="height: 1000px; width: 5px; position: absolute; top: 0; background: black;"
         style:left={(ctx.currentTime * 1000 - startTime) * scaling + "px"}></div>
</div>

<script lang="ts">
    import {BnkBdlFileReader, MusicSwitchNode} from "./lib/HIRCNodes";
  import Wwebplayer from "./Wwebplayer.svelte";
  import WWisualizer from "./WWisualizer.svelte";

  let manifest;
  let reader;

  let sw_nodes: MusicSwitchNode[];
  let active_sw_node;
  let ctx;

  $: is_playing_store = sw_nodes?sw_nodes[active_sw_node].now_playing:null;

  async function open() {
      const ip = document.createElement("input");
      ip.type = "file";
      ip.addEventListener("change", async event => {
          reader = new BnkBdlFileReader(ip.files![0]);
          await reader.validate();
          manifest = await reader.get_main_json();
      });
      ip.click();
  }

  function close() {
      manifest = null;
      reader = null;
  }
</script>

<style>

</style>

<main>
    {#if manifest}
        <Wwebplayer bind:ctx bind:sw_nodes bind:active_sw_node stop_on_destroy={true} debug_ran_seqs={false} debug_segments={false} {manifest} file_reader={reader}/>
        <button on:click={close}>close</button>
        <br/>
        <br/>
        <br/>
        {#if $is_playing_store}
            <WWisualizer {ctx} randomSequence={sw_nodes[active_sw_node].playing_rseq}/>
        {/if}
    {:else}
        <button on:click={open}>open</button>
    {/if}
</main>

<script lang="ts">
  /**
   * StreamViz Widget Component for Svelte 5
   *
   * Embeds a real-time StreamViz widget via iframe.
   *
   * @example
   * ```svelte
   * <StreamVizWidget widgetId="revenue" class="h-32 w-full" />
   * ```
   */

  interface Props {
    widgetId: string;
    serverUrl?: string;
    class?: string;
  }

  let { widgetId, serverUrl = "http://localhost:3000", class: className = "" }: Props = $props();

  function handleError() {
    console.warn(`StreamViz widget "${widgetId}" failed to load`);
  }
</script>

<iframe
  src="{serverUrl}/embed/{widgetId}"
  class={className}
  title="StreamViz {widgetId}"
  on:error={handleError}
></iframe>

<style>
  iframe {
    border: none;
    width: 100%;
    height: 100%;
  }
</style>

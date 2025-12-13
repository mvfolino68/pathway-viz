# Embedding Widgets

Embed PathwayViz widgets in your web app via iframes.

## Enable Embedding

```python
import pathway as pw
import pathway_viz as pv

orders = pw.io.kafka.read(...)
totals = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))

pv.configure(embed=True)
pv.stat(totals, "revenue", id="revenue", title="Revenue", embed=True)
pv.start()
pw.run()
```

Your script must keep running after `pv.start()`. If the Python process exits, the server stops.

Each widget is available at `http://localhost:3000/embed/{widget_id}`

## HTML

```html
<iframe
  src="http://localhost:3000/embed/revenue"
  style="border: none; width: 300px; height: 150px;"
></iframe>
```

## React / Next.js

```tsx
import { useEffect, useRef } from "react";

interface PathwayVizWidgetProps {
  widgetId: string;
  serverUrl?: string;
  className?: string;
  style?: React.CSSProperties;
}

export function PathwayVizWidget({
  widgetId,
  serverUrl = "http://localhost:3000",
  className = "",
  style,
}: PathwayVizWidgetProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    const handleError = () =>
      console.warn(`Widget "${widgetId}" failed to load`);
    iframe.addEventListener("error", handleError);
    return () => iframe.removeEventListener("error", handleError);
  }, [widgetId]);

  return (
    <iframe
      ref={iframeRef}
      src={`${serverUrl}/embed/${widgetId}`}
      className={className}
      style={{ border: "none", width: "100%", height: "100%", ...style }}
      title={`PathwayViz ${widgetId}`}
    />
  );
}
```

Usage:

```tsx
<PathwayVizWidget widgetId="revenue" className="h-32 w-full" />
```

## Svelte

```svelte
<script lang="ts">
  interface Props {
    widgetId: string;
    serverUrl?: string;
    class?: string;
  }

  let { widgetId, serverUrl = "http://localhost:3000", class: className = "" }: Props = $props();
</script>

<iframe
  src="{serverUrl}/embed/{widgetId}"
  class={className}
  title="PathwayViz {widgetId}"
  style="border: none; width: 100%; height: 100%;"
></iframe>
```

Usage:

```svelte
<PathwayVizWidget widgetId="revenue" class="h-32 w-full" />
```

## Notes

- Widgets connect via WebSocket automatically
- Transparent background—style the parent container
- Auto-reconnects on disconnect
- CORS enabled for any origin

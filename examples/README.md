# Framework Integration Examples

Embed StreamViz widgets into your web application via iframes.

## Run the Demo First

```bash
# For embedding examples, run the full demo (enables embed endpoints)
python -m stream_viz
```

This starts the full demo with Kafka/Redpanda, Pathway, and DuckDB persistence.

If you just want a quick sanity check without Docker:

```bash
python -m stream_viz --mode simple
```

---

## Framework Components

### React / Next.js

Copy `nextjs/StreamVizWidget.tsx` into your project:

```tsx
import { StreamVizWidget } from "./StreamVizWidget";

<StreamVizWidget widgetId="revenue" serverUrl="http://localhost:3000" />;
```

### Svelte 5

Copy `svelte/StreamVizWidget.svelte` into your project:

```svelte
<script>
  import StreamVizWidget from './StreamVizWidget.svelte';
</script>

<StreamVizWidget widgetId="revenue" serverUrl="http://localhost:3000" />
```

## Usage

1. Start StreamViz with embedding enabled:

   ```python
   import stream_viz as sv
   sv.configure(embed=True)
   sv.stat("revenue", title="Revenue", unit="$")
   sv.start()
   ```

2. Use the widget component in your app pointing to `http://localhost:3000/embed/revenue`

## Framework Examples

- **[Next.js](./nextjs/)** - React Server Components + Client embedding
- **[Svelte 5](./svelte/)** - Reactive widget components
- **[React](./react/)** - Simple React component wrapper

## Embedding API

Each widget is available at:

```
http://localhost:{port}/embed/{widget_id}
```

The embedded widget:

- Connects via WebSocket automatically
- Has transparent background (inherits parent styling)
- Resizes to fit container
- Reconnects on disconnect

## Tips

1. **Use iframes for isolation** - Each widget manages its own WebSocket connection
2. **Set explicit dimensions** - Wrap iframes in sized containers
3. **CORS is enabled** - Embed from any origin
4. **Transparent backgrounds** - Style the parent container, not the iframe

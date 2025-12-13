# PathwayViz Documentation

PathwayViz turns streaming data into a live dashboard you can also embed inside your own product.

You define widgets in Python, stream updates (manually or via Pathway), and PathwayViz serves:

- a dashboard at `/`
- per-widget embeds at `/embed/{widget_id}` (iframes)

Start with **[Getting Started](./getting-started.md)**.

After your first pipeline runs, the usual next steps are:

- enable embedding and add `<iframe ...>` tags in your app
- deploy with Docker

## Guides

| I want to...              | Read this                               |
| ------------------------- | --------------------------------------- |
| Set up my first dashboard | [Getting Started](./getting-started.md) |
| Add widgets               | [Widgets](./widgets.md)                 |
| Embed in my web app       | [Embedding](./embedding.md)             |
| Deploy to production      | [Deployment](./deployment.md)           |
| Understand how it works   | [Concepts](./concepts.md)               |

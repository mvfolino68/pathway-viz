# PathwayViz Documentation

PathwayViz provides embeddable real-time widgets for Pathway streaming pipelines.

You define widgets in Python, register them with a `WidgetServer`, and embed them anywhere via iframe:

- Widget overview at `/`
- Per-widget embeds at `/embed/{widget_id}`

Start with **[Getting Started](./getting-started.md)**.

After your first widget server runs, the usual next steps are:

- Add `<iframe src="http://localhost:3000/embed/{widget_id}">` tags in your app
- Deploy with Docker

## Guides

| I want to...             | Read this                               |
| ------------------------ | --------------------------------------- |
| Set up my first widgets  | [Getting Started](./getting-started.md) |
| Learn about widget types | [Widgets](./widgets.md)                 |
| Embed in my web app      | [Embedding](./embedding.md)             |
| Deploy to production     | [Deployment](./deployment.md)           |
| Understand how it works  | [Concepts](./concepts.md)               |

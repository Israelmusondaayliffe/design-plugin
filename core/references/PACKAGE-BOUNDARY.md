# Package Boundary

The distributed plugin may contain shared design methodology, compact craft guidance, schemas, templates, and a small catalog manifest.

It must not contain:

- Refero MCP configuration or runtime calls.
- Refero catalog records.
- The full independent Design Knowledge Corpus.
- The generated reference Site.
- `node_modules`, browser binaries, fonts, screenshots, renders, or benchmark project data.
- Secrets, credentials, personal context, or client information.

Host-specific files belong only in their host overlay. Shared files must be byte-identical in both generated distributions.

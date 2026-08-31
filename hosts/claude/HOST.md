# Claude Code Host Overlay

User-visible Claude Code workflows:

- `/design:run` for a new design project
- `/design:audit` for an existing interface
- `/design:resume` for an interrupted project with durable state

The Run skill may activate automatically for unmistakable end-to-end website, product-interface, mobile, Claude Artifact-to-site, redesign, or design-system work. Backend-only work, deployment-only work, document summarization, and unrelated image generation are excluded. Audit and Resume take precedence when their narrower signals are present.

The other nineteen skills are internal workflow phases. Their frontmatter sets `user-invocable: false`, so they remain available to Claude without appearing as standalone slash commands.

The Claude edition must detect available browser, image, Figma, and development capabilities rather than assume them. When no image tool exists, it produces implementation-ready GPT Image 2 or Midjourney prompts and continues with an honest asset placeholder or supplied asset according to the approved media strategy.

See `INSTALL.md` for build, install, update, and removal commands. Those commands change the selected Claude Code installation and require explicit approval before use.

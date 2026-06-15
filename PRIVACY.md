# Privacy Policy

_Last updated: June 13, 2026_

PaperView ("the plugin") is an open-source tool that runs **locally on your machine**. It is not a
hosted service, it has no user accounts, and the project operates no servers.

## What PaperView collects

**Nothing.** PaperView contains no analytics, telemetry, tracking, or "phone-home" of any kind. It
does not collect, store, or transmit your personal data, your input documents, your generated
videos, or any usage information to the project or its author.

## What stays on your machine

Your input files (PDFs, source code, text), the intermediate artifacts (parsed text, narration
audio, scene plans), and the final rendered video are all created and stored **only in a local
working directory** under `~/.paperview/`. Nothing is uploaded.

## Network access

PaperView makes outbound network requests only to **fetch public resources you've asked it to use**:

- On first `/ppv:setup`, it downloads open-source models and dependencies (the Kokoro TTS model,
  Remotion's headless browser, and Python/Node packages) from their official sources
  (e.g. GitHub, PyPI, npm).
- When you pass a **GitHub URL**, it clones that public repository to your local machine.
- When you reference an **arXiv paper**, it fetches that paper's public PDF and/or LaTeX source
  from arXiv.

These requests fetch data **to** your machine; they do not send your personal data anywhere.

## Third parties

- The **planning and scripting** are performed by the **Claude Code** agent you run PaperView
  inside. Your interactions with Claude Code are governed by
  [Anthropic's Privacy Policy](https://www.anthropic.com/legal/privacy), not this one.
- Model and package downloads are subject to the terms and privacy practices of the hosts that
  serve them (e.g. GitHub, PyPI, npm, arXiv).

## Contact

Questions? Open an issue at https://github.com/ssrajadh/paperview/issues.

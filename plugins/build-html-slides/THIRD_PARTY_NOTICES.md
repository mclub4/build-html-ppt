# Third-Party Notices

Parts of `references/korean-copy.md` are adapted from
[`epoko77-ai/im-not-ai`](https://github.com/epoko77-ai/im-not-ai).

Copyright (c) 2026 epoko77-ai

Licensed under the MIT License:

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Archify

The independent `archify` skill bundled under `codex/skills/archify` and its
platform mirrors is distributed from
[`tt-a1i/archify`](https://github.com/tt-a1i/archify), version 2.12.0,
commit `324c0c063bd5f89a36a582fcb9a3efb53caa4285`. The imported upstream
package has SHA-256 `3a52613634287fe90f39f076c98cb1271cce58737458e632e7766e1a6b443849`.

Copyright (c) 2026 tt-a1i (Archify)
Copyright (c) 2025 Cocoon AI (original "architecture-diagram-generator")

Archify is licensed under the MIT License. The complete upstream license and
copyright notice are preserved in every bundled `archify/LICENSE` file.
Archify identifies itself as a fork and rewrite of
[`Cocoon-AI/architecture-diagram-generator`](https://github.com/Cocoon-AI/architecture-diagram-generator)
v1.0; that upstream attribution is retained here and in the bundled license.

This distribution applies two narrow local integration patches to the pinned
Archify copy: newly rendered artifacts start in the light theme so slide
integration does not implicitly impose a dark technical style, and stale
example references in `SKILL.md` point to examples that are actually included
in the package. These changes are maintained by the Build HTML Slides project
and are not represented as upstream Archify behavior.

## Inter font test fixture

The validation test suite includes the Inter Latin Regular WOFF2 fixture from
`@fontsource/inter` 5.3.0 solely to exercise portable-font loading and
inspection.

Copyright 2020 The Inter Project Authors

Inter is licensed under the SIL Open Font License, Version 1.1. The complete
license is preserved at
`codex/skills/build-html-slides/scripts/fixtures/INTER-LICENSE.txt` and in each
platform mirror.

# Concept Workflow Instructions

This folder is the album ideation and Suno prep workspace for Rockit.

## Canonical Files

- `concept/album-outline.md`: the album-level source of truth
- `concept/instructions.md`: the durable workflow contract for future Codex sessions
- `concept/songs/*.md`: hand-editable per-track Suno working files

## Default Workflow

1. Read `concept/album-outline.md` first.
2. Read this file before generating or editing any `concept/songs/*.md` files.
3. Check which `concept/songs/*.md` files already exist.
4. Create only missing track files by default.
5. Do not overwrite or refresh existing song files unless the user explicitly asks to regenerate, refresh, or replace them.
6. Treat every existing song file as a user-owned working document.
7. Keep one active album in `concept/` at a time. Do not introduce a multi-album directory structure in v1.
8. Do not add a parser, CLI, or machine-strict schema in v1. This workflow is agent-driven and markdown-first.

## Naming Convention

- Output directory: `concept/songs/`
- One file per track
- File name format: `NN-slug.md`
- Use zero-padded track numbers
- Slugs should be lowercase ASCII and strip brackets, punctuation, and file-extension-like suffix punctuation cleanly

## Per-Track File Contract

Use this structure exactly so future sessions stay consistent:

```md
# NN. Working Title

## Source Intent
- Act:
- Entity / Theme:
- BPM Target:
- Style Anchors:
- Narrative Role:
- Lyrical Intent:
- Telegraph Cue:
- Suno Notes:

## Suno Title

## Suno Style Prompt

## Suno Lyrics

Use section labels plus inline stage-direction notes in square brackets, since Suno v4.5 can interpret those cues.
Embed arrangement, vocal-delivery, and section-shape guidance directly inside the lyric block instead of keeping them in passive note sections.

## Suno Options
- BPM Target:
- Vocal Gender:
- Lyrics Mode:
- Weirdness:
- Style Influence:
- Constraints:

## Negative Prompt

bright EDM festival leads, clean pop vocals, goofy novelty framing, overly dense or overwritten phrasing

## Alternate Ideas
- Alternate title:
- Alternate hook:
- Alternate style twist:

## Operator Notes
- Paste `Suno Title` into the title field.
- Paste `Suno Style Prompt` into the style / genre prompt field.
- Paste `Suno Lyrics` into custom lyrics, including the inline bracketed direction notes.
- Start with the BPM target and the embedded lyric cues if the first generation misses the feel.
```

## Content Rules For Generated Song Files

- Write the file from the outline, not from scratch.
- Keep the track identity aligned to the album arc, act, and entity/theme in `concept/album-outline.md`.
- Include the expanded pack by default:
  - title
  - style prompt
  - full lyrics
  - BPM / tempo target
  - Suno options
  - negative prompt
  - alternate ideas
  - operator notes
- Telegraph cues should appear in the lyrics when the track outline includes one.
- Lyrics should be paste-ready for Suno, with clear section labels when useful.
- Because this workflow targets Suno v4.5, inline square-bracket stage directions should be used inside lyrics when they improve delivery, transitions, emphasis, or production feel.
- Do not keep separate arrangement, vocal, or section-note blocks in the generated song files; those cues belong inside `## Suno Lyrics`.
- Prefer short, chantable, techno-native phrasing: fewer explanatory lines, more repeated command language, and one or two strong mantra hooks per track.
- Unless a track explicitly overrides it, use these Suno defaults: `Vocal Gender = Female`, `Lyrics Mode = Manual`, `Weirdness = 50`, `Style Influence = 50`.
- If a file already exists and the user has not asked for regeneration, leave it alone.

## Regeneration Rules

- "Generate" means create missing files only.
- "Refresh" or "regenerate" means replace only the files the user names.
- If the user explicitly asks to redo the entire album set, then all track files may be replaced.
- Preserve the same file names unless the source track title changes in `concept/album-outline.md`.

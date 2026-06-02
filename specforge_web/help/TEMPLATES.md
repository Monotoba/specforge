# Artifact Templates

Templates prefill the body and metadata of new artifacts so you never
start from a blank page. Drop a Markdown file into
`.specforge/templates/<kind>.md` and it becomes the default for that
artifact kind.

---

## Built-in templates

SpecForge creates starter templates for `requirement`, `task`, and
`test` when you run `specforge init`. You can edit them at any time.

---

## Template format

A template is a Markdown file with optional YAML front matter:

```markdown
---
tags: [v1.0]
status: draft
---

## Purpose

<!-- What this artifact achieves and why it matters -->

## Acceptance criteria

- [ ]
```

**Front matter** (between `---` lines) is optional. Supported keys:

| Key | Effect |
|-----|--------|
| `tags` | Added to the artifact's tag list when created |
| `status` | Overrides the default status for this kind |

**Body** (below the front matter) becomes the artifact's Markdown body.

---

## Creating and editing templates

```bash
# List available templates
specforge template ./proj list

# Edit an existing template in $EDITOR
specforge template ./proj edit requirement
specforge template ./proj edit task
specforge template ./proj edit test

# Create a template for a kind that doesn't have one yet
specforge template ./proj edit idea
```

If the template file doesn't exist yet, `edit` creates an empty one
and opens it. Set `$VISUAL` or `$EDITOR` in your shell:

```bash
export EDITOR=nano    # or vim, code, micro, etc.
```

---

## Using a template

```bash
# Create a requirement from template (opens confirmation prompt)
specforge template ./proj new requirement --title "Export DXF files"

# Skip the confirmation prompt
specforge template ./proj new task --title "Implement batch export" --no-confirm

# Add tags at creation time (merged with template tags)
specforge template ./proj new test --title "DXF round-trip" --tag v1.0 --git
```

The template body is shown in a Rich panel before confirmation. Press
Enter or `y` to create, `n` to cancel.

---

## Template file locations

Templates live inside the project at:

```
<project-root>/
  .specforge/
    templates/
      requirement.md
      task.md
      test.md
      <any-kind>.md
```

Any file named `<kind>.md` where `<kind>` matches a valid artifact kind
is a valid template. Templates are committed to git along with your
project (they are in `.specforge/templates/`, not in `.gitignore`).

---

## Example templates

### Requirement template

```markdown
---
tags: []
---

## Purpose

<!-- What user need or system behaviour this requirement addresses -->

## Acceptance criteria

- [ ] 

## Out of scope

<!-- What this requirement explicitly does NOT cover -->
```

### Task template

```markdown
---
tags: []
---

## What

<!-- A concise description of the work to be done -->

## Done when

- [ ] 

## Notes

<!-- Implementation notes, links to relevant code, gotchas -->
```

### Test template

```markdown
---
tags: []
---

## Test objective

<!-- What behaviour is being verified -->

## Prerequisites

<!-- Environment, data, configuration needed before running the test -->

## Steps

1. 
2. 

## Expected result

<!-- What a passing test looks like -->
```

---

## Tips

- Keep templates short — they are starting points, not finished
  documents.
- Use `<!-- comment -->` for inline guidance that will be visible in
  the editor but is harmless to leave in.
- Pair templates with AI drafting: use `specforge draft` when you want
  AI-generated content, and `specforge template new` when you want a
  structured blank slate.

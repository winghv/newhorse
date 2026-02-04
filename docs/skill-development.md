# Skill Development Guide

Skills are modular capabilities that agents can use. They define specific workflows, reference documentation, and helper scripts.

## Overview

A skill consists of:

- **SKILL.md** - The skill definition with metadata and instructions
- **scripts/** - Optional helper scripts for deterministic operations
- **references/** - Optional detailed documentation

## Creating a Skill

### Step 1: Generate Template

```bash
npm run new:skill my-skill
```

Creates:
```
extensions/skills/my-skill/
├── SKILL.md
├── scripts/
│   └── helper.py
└── references/
```

### Step 2: Define the Skill

Edit `SKILL.md`:

```markdown
---
name: my-skill
description: Brief description of what this skill does and when to trigger it
version: 1.0.0
---

# My Skill

## Overview

[Detailed description of what this skill does]

## When to Use

This skill should be triggered when:
- Condition 1
- Condition 2
- User mentions specific keywords

## Workflow

1. [First step]
2. [Second step]
3. [Third step]

## Examples

User: "Do the thing"
Agent: [Expected response/action]
```

## SKILL.md Structure

### Frontmatter (Required)

```yaml
---
name: skill-name           # Unique identifier (kebab-case)
description: Brief desc    # CRITICAL for triggering
version: 1.0.0            # Semantic version
---
```

### Body Sections

1. **Overview** - What the skill does
2. **When to Use** - Trigger conditions
3. **Workflow** - Step-by-step process
4. **Examples** - Usage examples
5. **Tools/APIs** - Required tools or integrations

## The Description Field

The `description` field is crucial - it determines when the skill is triggered.

### Good Descriptions

```yaml
description: Generate unit tests for Python code. Use when user asks for tests, test coverage, or testing help.
```

```yaml
description: Analyze and optimize SQL queries. Trigger for slow queries, query optimization, or database performance.
```

### Bad Descriptions

```yaml
description: A helpful skill  # Too vague
```

```yaml
description: Does stuff  # Not descriptive
```

## Adding Scripts

Scripts handle deterministic operations that code does better than LLMs.

### Example Script

```python
#!/usr/bin/env python3
"""
scripts/analyzer.py - Analyze code metrics
"""
import sys
import json

def analyze(file_path):
    # Deterministic analysis
    with open(file_path) as f:
        content = f.read()

    return {
        "lines": len(content.split('\n')),
        "characters": len(content),
    }

if __name__ == "__main__":
    result = analyze(sys.argv[1])
    print(json.dumps(result, indent=2))
```

### When to Use Scripts

- Data transformation
- File processing
- Calculations
- API calls with specific logic
- Anything requiring deterministic output

## Adding References

Reference files provide detailed documentation the agent can read when needed.

### Structure

```
references/
├── api-docs.md       # API documentation
├── schema.md         # Database schema
└── examples/         # Example files
    ├── example1.py
    └── example2.py
```

### In SKILL.md

```markdown
## References

For detailed API documentation, see `references/api-docs.md`.
For database schema, see `references/schema.md`.
```

## Best Practices

### Keep SKILL.md Focused

- Under 500 lines
- Core workflow only
- Reference external docs for details

### Provide Clear Triggers

- List specific conditions
- Include example phrases
- Be explicit about scope

### Use Progressive Disclosure

1. Frontmatter: Always in context
2. SKILL.md body: Loaded when triggered
3. References: Read on demand

### Test Your Skills

1. Create a project with the agent that uses your skill
2. Try different trigger phrases
3. Verify the workflow executes correctly
4. Check edge cases

## Example Skills

### Code Formatter Skill

```markdown
---
name: code-formatter
description: Format code according to style guides. Use for formatting, linting, or code style questions.
---

# Code Formatter

## Workflow

1. Identify the programming language
2. Read the file content
3. Apply appropriate formatting rules
4. Write the formatted content

## Supported Languages

- Python (Black)
- JavaScript (Prettier)
- Go (gofmt)
```

### Database Query Skill

```markdown
---
name: db-query
description: Generate and execute database queries. Use for SQL, data retrieval, or database operations.
---

# Database Query Skill

## Workflow

1. Understand the data requirement
2. Identify relevant tables
3. Generate optimized SQL
4. Execute and format results

## Available Tables

See `references/schema.md` for the complete database schema.
```

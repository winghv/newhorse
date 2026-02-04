# Demo Skill Reference Guide

## Detailed Documentation

This file contains additional reference documentation for the demo skill.
The agent can read this file when more detailed information is needed.

## Best Practices for Skills

### 1. Keep SKILL.md Focused

The main SKILL.md file should be:
- Under 500 lines
- Focused on the core workflow
- Clear about trigger conditions

### 2. Use References for Details

Put detailed documentation in the references/ directory:
- API documentation
- Database schemas
- External service guides

### 3. Scripts for Deterministic Operations

Use scripts when you need:
- Data transformation
- File processing
- External API calls with specific logic
- Calculations

### 4. Description is Key

The `description` field in SKILL.md frontmatter determines when the skill is triggered.
Include:
- What the skill does
- When to use it
- Keywords users might use

## Example Skills

Here are some ideas for skills you might create:

1. **code-review**: Analyze code and provide feedback
2. **git-helper**: Assist with git operations
3. **doc-generator**: Generate documentation
4. **test-writer**: Write test cases
5. **api-designer**: Design REST APIs

## Integration with Agents

Skills are loaded by agents based on their configuration.
In the agent's `init_claude_option` method:

```python
options = ClaudeAgentOptions(
    skillsDirectories=["/path/to/skills"],
    # ...
)
```

The agent will automatically discover and load skills from the specified directories.

/**
 * Create a new skill template
 */
const fs = require('fs');
const path = require('path');

const skillName = process.argv[2];

if (!skillName) {
    console.log('Usage: npm run new:skill <skill-name>');
    console.log('Example: npm run new:skill my-awesome-skill');
    process.exit(1);
}

const skillsDir = path.join(__dirname, '..', 'extensions', 'skills');
const skillPath = path.join(skillsDir, skillName);

if (fs.existsSync(skillPath)) {
    console.error(`Skill "${skillName}" already exists`);
    process.exit(1);
}

// Create directories
fs.mkdirSync(path.join(skillPath, 'scripts'), { recursive: true });
fs.mkdirSync(path.join(skillPath, 'references'), { recursive: true });

// Create SKILL.md
const skillMd = `---
name: ${skillName}
description: [Describe what this skill does and when to use it]
version: 1.0.0
---

# ${skillName.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}

## Overview

[Describe what this skill does]

## When to Use

This skill is triggered when:
- [Condition 1]
- [Condition 2]

## Workflow

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Examples

[Provide usage examples]
`;

fs.writeFileSync(path.join(skillPath, 'SKILL.md'), skillMd);

// Create example script
const scriptPy = `#!/usr/bin/env python3
"""
${skillName} helper script
"""

def main():
    print("Hello from ${skillName}!")

if __name__ == "__main__":
    main()
`;

fs.writeFileSync(path.join(skillPath, 'scripts', 'helper.py'), scriptPy);

console.log(`✅ Created skill: ${skillName}`);
console.log(`   ${skillPath}/`);
console.log(`   ├── SKILL.md`);
console.log(`   ├── scripts/`);
console.log(`   │   └── helper.py`);
console.log(`   └── references/`);
console.log('');
console.log('Next steps:');
console.log(`1. Edit ${path.join(skillPath, 'SKILL.md')}`);
console.log('2. Add scripts as needed');
console.log('3. Add reference docs as needed');

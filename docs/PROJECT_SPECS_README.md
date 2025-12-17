# Project Specifications Management

The autonomous agent framework now supports organized project specifications stored in `prompts/{project_name}/` directories. This allows you to maintain a library of reusable project specs.

## Directory Structure

```
github-coding-agent-framework/
├── prompts/
│   ├── initializer_prompt.md
│   ├── coding_prompt.md
│   ├── test_fresh/
│   │   └── app_spec.txt
│   ├── my-saas-app/
│   │   └── app_spec.txt
│   └── ecommerce-site/
│       └── app_spec.txt
└── generations/
    ├── test_fresh/        # Generated project
    └── my-saas-app/       # Generated project
```

## Managing Project Specs

### List All Available Specs

```bash
python manage_specs.py list
```

Output:
```
Available Project Specifications:
============================================================
  * test_fresh                     AI-POWERED MULTI-BRAND BUSINESS AUTOMATI
  * my-saas-app                    SaaS Application Platform
============================================================

Total: 2 project(s)
```

### Create a New Project Spec

```bash
python manage_specs.py create my-new-project
```

This creates:
- `prompts/my-new-project/` directory
- `prompts/my-new-project/app_spec.txt` with a template

### View a Project Spec

```bash
python manage_specs.py view test_fresh
```

### Edit a Project Spec

```bash
python manage_specs.py edit test_fresh
```

Opens the spec in your default text editor (Notepad on Windows).

## Running the Agent with a Spec

### Using Project Name (Recommended)

```bash
python autonomous_agent_fixed.py \
  --project-dir ./generations/my-project \
  --project-name test_fresh \
  --max-iterations 5
```

This will:
1. Look for `prompts/test_fresh/app_spec.txt`
2. Copy it to `generations/my-project/app_spec.txt`
3. Create GitHub repo based on spec content
4. Create 50 issues from the spec
5. Start building the project

### Using Directory Name (Automatic)

```bash
python autonomous_agent_fixed.py \
  --project-dir ./generations/test_fresh
```

Automatically looks for `prompts/test_fresh/app_spec.txt` based on the directory name.

### Legacy Mode

If no project-specific spec is found, it falls back to `prompts/app_spec.txt` (if it exists).

## Spec Lookup Order

When you run the agent, it looks for app_spec.txt in this order:

1. `prompts/{--project-name}/app_spec.txt` (if --project-name provided)
2. `prompts/{directory-name}/app_spec.txt` (based on --project-dir name)
3. `prompts/app_spec.txt` (legacy fallback)

## Benefits

### 1. **Project Library**
Maintain a collection of reusable project specifications:
- `prompts/saas-starter/` - SaaS application template
- `prompts/ecommerce/` - E-commerce site template
- `prompts/dashboard/` - Analytics dashboard template

### 2. **Version Control**
All your project specs are tracked in git:
```bash
git add prompts/my-project/app_spec.txt
git commit -m "Add new project spec: my-project"
```

### 3. **Collaboration**
Share project specs with your team through the repository.

### 4. **Reusability**
Use the same spec to generate multiple variations:
```bash
# Generate project for client A
python autonomous_agent_fixed.py --project-dir ./generations/clientA-site --project-name ecommerce

# Generate project for client B
python autonomous_agent_fixed.py --project-dir ./generations/clientB-site --project-name ecommerce
```

## Example Workflow

1. **Create a new spec:**
   ```bash
   python manage_specs.py create my-saas-app
   ```

2. **Edit the spec:**
   ```bash
   python manage_specs.py edit my-saas-app
   ```

   Add your project requirements, features, tech stack, etc.

3. **Run the agent:**
   ```bash
   python autonomous_agent_fixed.py --project-dir ./generations/my-saas-v1 --project-name my-saas-app
   ```

4. **The agent will:**
   - Copy spec to `generations/my-saas-v1/app_spec.txt`
   - Create GitHub repo: `ProvidenceIT/my-saas-app` (or similar)
   - Create 50 issues from the spec
   - Start implementation

5. **Reuse for another version:**
   ```bash
   python autonomous_agent_fixed.py --project-dir ./generations/my-saas-v2 --project-name my-saas-app
   ```

## Tips

- **Keep specs generic**: Write specs that can be reused across similar projects
- **Use descriptive names**: `clevertech-crm` is better than `project1`
- **Document well**: The first 20 lines of your spec determine the GitHub repo name
- **Version control**: Commit spec changes to track evolution of your project templates
- **Start simple**: Begin with a basic template and refine it over time

## Migrating Existing Projects

If you have an existing `generations/my-project/app_spec.txt` that you want to save:

```bash
# Create the spec directory
mkdir -p prompts/my-project

# Copy the spec
cp generations/my-project/app_spec.txt prompts/my-project/app_spec.txt

# Commit to git
git add prompts/my-project/
git commit -m "Add my-project spec to library"
```

Now you can reuse this spec for new projects!

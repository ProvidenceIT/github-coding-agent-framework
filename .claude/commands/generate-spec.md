---
name: generate-spec
description: Generate a comprehensive app_spec.txt file from project requirements
tags: [planning, specification, automation]
---

# Generate App Specification

Create a detailed `app_spec.txt` file ready for the autonomous coding agent.

## Input Requirements

Provide the following information:

### 1. Project Overview
- **Name**: Application name
- **Description**: Brief overview (2-3 sentences)
- **Purpose**: What problem does it solve?
- **Target Users**: Who will use this?

### 2. Core Features
List your must-have features. I'll expand these into detailed specifications.

Example:
- User authentication
- Dashboard with analytics
- Real-time chat
- File uploads
- etc.

### 3. Technology Stack
Specify or let me recommend:
- Frontend framework
- Backend framework
- Database
- Authentication method
- Hosting platform

### 4. Design Requirements
- UI style (modern, minimal, corporate, etc.)
- Color scheme (if any)
- Accessibility requirements (WCAG level)
- Responsive design needs (mobile, tablet, desktop)

## What I'll Generate

A comprehensive `app_spec.txt` containing:

### Project Metadata
```
Project Name: [Your App]
Type: Full-stack web application
Tech Stack: [Recommended stack]
```

### Feature Breakdown
50+ detailed feature specifications:
- **Functional features**: Authentication, CRUD operations, APIs
- **Style features**: UI components, responsive design, animations
- **Infrastructure**: Build, deployment, monitoring

Each feature includes:
- Description
- Acceptance criteria
- Test steps
- Priority level (urgent, high, medium, low)

### Technical Requirements
- Frontend architecture
- Backend architecture
- Database schema guidelines
- API design patterns
- Security requirements
- Performance targets

### Quality Standards
- Testing requirements (unit, integration, E2E)
- Accessibility compliance
- Browser compatibility
- Performance benchmarks

### Deployment Plan
- Build process
- Environment configuration
- Deployment strategy
- Monitoring and logging

---

## Output Location

The generated spec will be saved to:
```
prompts/app_spec.txt
```

Ready to use with:
```bash
python autonomous_agent_demo.py --project-dir ./generations/your_app
```

---

## Let's Start

Provide your project requirements and I'll generate a comprehensive specification file.

Alternatively, use the `/idea-to-spec` command for a guided interactive process.

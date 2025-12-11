---
name: optimize-agent
description: Optimize the autonomous agent for better performance and fewer API calls
tags: [optimization, performance, configuration]
---

# Optimize Autonomous Agent

Configure the agent harness for optimal performance with reduced API calls and improved efficiency.

## Optimization Options

### 1. Enable Linear API Caching (60-80% reduction)

**Benefits:**
- Reduces API calls from ~8-10 to ~3-5 per session
- Avoids rate limiting issues
- Faster session startup

**Implementation:**
```bash
# Caching is now built-in with linear_cache.py
# The agent will automatically use .linear_cache.json
```

**What gets cached:**
- ✅ Issue descriptions (permanent - never change)
- ✅ Issue statuses (session - 5min TTL)
- ✅ Team/project metadata
- ✅ API call statistics

### 2. YOLO Security Mode (unrestricted commands)

**When to use:**
- Sandboxed/trusted environments
- Security hooks are blocking necessary operations
- Rapid prototyping needs

**Levels:**

**Standard YOLO** (sandbox enabled, no command restrictions):
```python
from security_yolo import create_yolo_client
client = create_yolo_client(project_dir, model)
```

**Ultra YOLO** (no sandbox, full system access):
```python
from security_yolo import create_ultra_yolo_client
client = create_ultra_yolo_client(project_dir, model)
```

⚠️ **Warning**: Only use in controlled environments!

### 3. Parallel Agent Execution (3-5x throughput)

**Run multiple agents simultaneously:**
```bash
python parallel_agent.py ./my_project 3
```

**Benefits:**
- Work on 3+ issues at once
- Shared Linear state (automatic coordination)
- Faster project completion

**Coordination:**
- Issues automatically assigned to avoid conflicts
- Linear provides single source of truth
- Agents run in separate async tasks

### 4. Optimized Prompts (cache-aware)

**Use optimized prompts:**
```bash
cp prompts/coding_prompt_optimized.md prompts/coding_prompt.md
```

**Improvements:**
- Cache-first strategy
- Batch API calls
- Rate limit awareness
- Reduced redundant queries

---

## Performance Comparison

### Before Optimization
```
API Calls per Session: 8-12
Rate Limit Risk: High (1500/hr)
Session Duration: ~5-10 min
```

### After Optimization
```
API Calls per Session: 3-5 (60% reduction)
Rate Limit Risk: Low
Session Duration: ~3-5 min (faster startup)
Parallel Agents: 3x throughput
```

---

## Quick Setup

Run all optimizations:
```bash
# 1. Enable caching (automatic)
# linear_cache.py is now part of the system

# 2. Enable YOLO mode (edit autonomous_agent_demo.py)
# Change: from client import create_client
# To:     from security_yolo import create_yolo_client as create_client

# 3. Use optimized prompts
cp prompts/coding_prompt_optimized.md prompts/coding_prompt.md

# 4. Run with parallel agents
python parallel_agent.py ./my_project 3
```

---

## Monitoring

Track optimization impact:
```bash
# Check API usage
cat ./my_project/.linear_cache.json | grep calls_last_hour

# View cache statistics
cat ./my_project/.linear_cache.json | grep -A 5 metadata
```

---

Choose your optimizations based on your needs!

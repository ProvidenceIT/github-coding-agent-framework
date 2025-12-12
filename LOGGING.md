# Comprehensive Debug Logging

The `autonomous_agent_fixed.py` script now includes comprehensive debug logging to help diagnose issues and understand agent behavior.

## Log File Location

Session logs are written to: `<project_dir>/logs/session_TIMESTAMP.log`

Example: `./generations/my_project/logs/session_20231211_143022.log`

## What's Logged

### 1. Client Creation
- When the Claude Code client is created
- Client options used:
  - Model name
  - System prompt
  - Allowed tools
  - Max turns
- Time taken to create and connect

### 2. Prompt Information
- First 500 characters of each prompt sent
- Full prompt length
- Mode (Initializer vs Coding)

### 3. Agent Response
- Full agent response (DEBUG level)
- Response duration
- Tool usage count (if available)
- Session timing

### 4. Tool Usage
- Attempts to extract tool call count from response
- Logs tool call details when available
- Estimates tool usage from response text

### 5. Errors and Exceptions
- Error type and message
- Full stack trace
- Duration before error occurred
- Context about which operation failed

### 6. Session Timing
- Individual session duration
- Total iteration duration
- Total run duration
- Average iteration time

### 7. Git Operations
- Commit and push attempts
- Success/failure messages

## Log Levels

The logging system uses multiple levels:

- **DEBUG**: Verbose details (full responses, stack traces, internal operations)
- **INFO**: Key events (session start/end, client creation, timing summaries)
- **WARNING**: Non-critical issues (failed commits with no changes)
- **ERROR**: Exceptions and failures

## Console vs File Logging

- **Console**: Shows INFO level and above (less verbose)
- **File**: Shows DEBUG level and above (complete details)

## Log Format

```
YYYY-MM-DD HH:MM:SS | LEVEL    | logger_name | message
```

Example:
```
2023-12-11 14:30:22 | INFO     | autonomous_agent | STARTING AGENT SESSION: session_20231211_143022_001
2023-12-11 14:30:22 | DEBUG    | autonomous_agent | PROMPT SENT (1234 chars): You are an expert...
2023-12-11 14:30:45 | INFO     | autonomous_agent | AGENT RESPONSE RECEIVED (duration: 23.45s)
```

## Viewing Logs

### Tail the log in real-time:
```bash
tail -f ./generations/my_project/logs/session_*.log
```

### Search for errors:
```bash
grep "ERROR" ./generations/my_project/logs/session_*.log
```

### View timing information:
```bash
grep "duration" ./generations/my_project/logs/session_*.log
```

### View tool usage:
```bash
grep "TOOL USAGE" ./generations/my_project/logs/session_*.log
```

## Log File Management

- New log file created for each agent run
- Old logs are NOT automatically deleted
- Log files are excluded from git via `.gitignore`
- Logs directory created automatically if it doesn't exist

## Debugging Tips

1. **Check client creation**: Look for "CREATING CLAUDE CODE CLIENT" section
2. **Verify prompt**: Check "PROMPT SENT" entries (first 500 chars logged)
3. **Review responses**: Full responses logged at DEBUG level
4. **Track timing**: Search for "duration" to identify slow operations
5. **Find errors**: Search for "ERROR" or "EXCEPTION" entries
6. **Tool usage**: Look for "TOOL USAGE COUNT" to verify agent activity

## Example Log Sections

### Successful Session:
```
================================================================================
STARTING AGENT SESSION: session_20231211_143022_001
================================================================================
DEBUG: PROMPT SENT (1234 chars): You are an expert...
DEBUG: Calling client.query()...
INFO: AGENT RESPONSE RECEIVED (duration: 23.45s)
INFO: TOOL USAGE COUNT: 5
INFO: SESSION TIMING: 23.45 seconds
INFO: ITERATION 1 COMPLETED in 25.67s
```

### Error Session:
```
================================================================================
ERROR DURING SESSION (duration: 15.23s)
ERROR: Error type: TimeoutError
ERROR: Error message: Connection timeout
ERROR: Stack trace:
Traceback (most recent call last):
  ...
================================================================================
```

## Integration with Development

When reporting issues or debugging:

1. Run the agent with logging enabled (automatic)
2. Reproduce the issue
3. Locate the relevant log file in `./logs/`
4. Share relevant log sections when reporting bugs
5. Use log timing to identify performance bottlenecks

The comprehensive logging ensures you can always see exactly what's happening during agent execution.

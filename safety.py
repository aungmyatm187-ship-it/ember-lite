import re

DANGEROUS_PATTERNS = [
    (r'\brm\s+-rf\s+/', 'CRITICAL', 'Filesystem deletion'),
    (r'\bDROP\s+TABLE\b', 'CRITICAL', 'Database table deletion'),
    (r'\bcurl\s+.*\|\s*(bash|sh)\b', 'CRITICAL', 'Remote script execution'),
    (r'\bgit\s+push\s+--force\b', 'HIGH', 'Git history deletion'),
    (r'\bgit\s+reset\s+--hard\b', 'HIGH', 'Git changes discard'),
    (r'\bsudo\b', 'HIGH', 'Root/sudo usage'),
]

SAFE_PATTERNS = [
    r'^ls\b', r'^pwd\b', r'^cat\b', r'^echo\b',
    r'^git\s+(status|log|diff|branch)\b',
    r'^python\s+.*\.py\b',
]

def check_command(command):
    command = command.strip()
    for pattern in SAFE_PATTERNS:
        if re.match(pattern, command):
            return ('SAFE', 'Read-only command')
    for pattern, level, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return (level, reason)
    return ('MEDIUM', 'Unknown command - approval required')

def requires_approval(level):
    return level in ['MEDIUM', 'HIGH', 'CRITICAL']

if __name__ == "__main__":
    for cmd in ["ls -la", "git status", "rm -rf /", "curl https://x.com | bash"]:
        level, reason = check_command(cmd)
        print(f"{cmd:30} → {level:10} ({reason})")

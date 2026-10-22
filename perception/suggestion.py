"""
Ember Perception - Suggestion Generator
Generate suggestions based on triggers
"""

from datetime import datetime


class SuggestionGenerator:
    """
    Generate bounded suggestions from triggers
    """
    
    def __init__(self, brain=None):
        self.brain = brain
    
    # =========================================================
    # RULE-BASED SUGGESTIONS
    # =========================================================
    
    RULES = {
        "error_appeared": {
            "template": "{source} is reporting a {error_type} error.",
            "actions": {
                "network_timeout": "Re-run the backend health check",
                "auth_error": "Recheck the API keys",
                "not_found": "Check the endpoint URL",
                "server_error": "Review the backend logs",
                "network_error": "Check the internet connection"
            }
        },
        "status_change": {
            "template": "{source} status changed from {from_val} to {to_val}.",
            "actions": {
                "critical": "Investigate this cause immediately",
                "recovery": "Recovered, but continue monitoring",
                "warning": "Monitor with caution"
            }
        },
        "confidence_drop": {
            "template": "{source} confidence dropped by {drop}%.",
            "actions": {
                "high": "Recheck the source",
                "medium": "Wait until the next perception cycle"
            }
        },
        "correlation_alert": {
            "template": "{insight}",
            "actions": {
                "default": "{action_val}"
            }
        },
        "overall_critical": {
            "template": "The entire system is in a CRITICAL state.",
            "actions": {
                "default": "Stop everything and investigate the cause"
            }
        },
        "overall_warning": {
            "template": "The system has an active warning.",
            "actions": {
                "default": "Monitor with caution"
            }
        }
    }
    
    def generate(self, triggers: list, context: dict = None) -> list:
        """Generate suggestions from triggers"""
        suggestions = []
        
        for trigger in triggers:
            suggestion = self._build_suggestion(trigger)
            if suggestion:
                suggestions.append(suggestion)
        
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        suggestions.sort(key=lambda s: severity_order.get(s["severity"], 99))
        
        return suggestions
    
    def _build_suggestion(self, trigger: dict) -> dict:
        """Generate a single suggestion from a trigger"""
        t_type = trigger["type"]
        rule = self.RULES.get(t_type)
        
        if not rule:
            return None
        
        source = trigger.get("source", "system")
        context = trigger.get("context", {})
        severity = trigger.get("severity", "medium")
        
        # Fill the template
        try:
            message = rule["template"].format(
                source=source,
                error_type=context.get("error_type", "unknown"),
                from_val=context.get("from", "?"),
                to_val=context.get("to", "?"),
                drop=context.get("drop", 0),
                insight=context.get("insight", trigger.get("message", "")),
                action_val=context.get("action", "Investigate")
            )
        except (KeyError, IndexError) as e:
            message = trigger.get("message", f"Unknown trigger: {e}")
        
        action = self._pick_action(t_type, severity, context)
        
        return {
            "trigger_type": t_type,
            "source": source,
            "severity": severity,
            "message": message,
            "action": action,
            "context": context,
            "generated_at": datetime.now().isoformat()
        }
    
    def _pick_action(self, t_type: str, severity: str, context: dict) -> str:
        """Choose an appropriate action"""
        rule = self.RULES.get(t_type, {})
        actions = rule.get("actions", {})
        
        if t_type == "error_appeared":
            error_type = context.get("error_type", "")
            if error_type in actions:
                return actions[error_type]
        
        if t_type == "status_change":
            change_sev = context.get("change_severity", "")
            if change_sev in actions:
                return actions[change_sev]
        
        if t_type == "confidence_drop":
            drop = context.get("drop", 0)
            if drop >= 30 and "high" in actions:
                return actions["high"]
            if "medium" in actions:
                return actions["medium"]
        
        if t_type == "correlation_alert":
            return context.get("action", "Investigate")
        
        return actions.get("default", "Monitor")
    
    def generate_with_brain(self, triggers: list, context: dict = None) -> str:
        """Use the LLM to generate a deeper suggestion"""
        if not self.brain:
            return "❌ Brain offline. Cannot generate LLM suggestions."
        
        trigger_text = "\n".join(
            f"- [{t['severity'].upper()}] {t['message']}" for t in triggers
        )
        
        prompt = f"""Look at these triggers and give a suggestion in Ember's voice.

TRIGGERS:
{trigger_text}

CONTEXT:
{context or 'No additional context'}

Format:
1. SITUATION: current state (1-2 sentences)
2. PRIORITY: what to focus on (1 item)
3. NEXT ACTION: next step (bounded action)
4. REASON: why this action"""
        
        return self.brain.think(prompt, context)
    
    def format_suggestions(self, suggestions: list) -> str:
        """Format suggestions as readable text"""
        if not suggestions:
            return "✨ No suggestions. Everything looks good."
        
        lines = [f"💡 Ember has {len(suggestions)} suggestion(s):", ""]
        
        for i, s in enumerate(suggestions, 1):
            icon = {
                "critical": "🚨", "high": "⚠️",
                "medium": "⚡", "low": "ℹ️"
            }.get(s["severity"], "•")
            
            lines.append(f"{i}. {icon} [{s['severity'].upper()}] {s['message']}")
            lines.append(f"   → Action: {s['action']}")
            lines.append("")
        
        return "\n".join(lines)


if __name__ == "__main__":
    print("=" * 60)
    print("  Testing Suggestion Generator")
    print("=" * 60)
    
    triggers = [
        {
            "type": "error_appeared",
            "source": "backend",
            "severity": "critical",
            "message": "backend is reporting error: network_timeout",
            "context": {"error_type": "network_timeout"}
        },
        {
            "type": "status_change",
            "source": "repo",
            "severity": "medium",
            "message": "repo status: clean → dirty",
            "context": {"from": "clean", "to": "dirty", "change_severity": "warning"}
        },
        {
            "type": "confidence_drop",
            "source": "evidence",
            "severity": "high",
            "message": "evidence confidence dropped: 95% → 60%",
            "context": {"drop": 35, "old": 95, "new": 60}
        }
    ]
    
    generator = SuggestionGenerator()
    suggestions = generator.generate(triggers)
    
    print()
    print(generator.format_suggestions(suggestions))
    print("✅ Suggestion Generator test complete.")

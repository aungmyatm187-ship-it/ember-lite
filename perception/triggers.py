"""
Ember Perception - Trigger Engine
Decide when to suggest
"""

from datetime import datetime


class TriggerEngine:
    """
    Evaluate trigger rules
    Examples: status change, confidence drop, new error
    """
    
    # Severity levels
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
    def __init__(self):
        self.triggers_fired = []
    
    def evaluate(self, analysis_report: dict) -> list:
        """
        Fire triggers based on the analysis report
        
        Args:
            analysis_report: output of P1 analysis
        
        Returns: List of triggered events
        """
        self.triggers_fired = []
        
        observations = analysis_report.get("observations", {})
        changes = analysis_report.get("changes", {})
        correlations = analysis_report.get("correlations", [])
        
        # Rule 1: Status Change (Recovery / Degradation)
        self._check_status_change(changes)
        
        # Rule 2: Confidence Drop
        self._check_confidence_drop(observations)
        
        # Rule 3: Error Appears
        self._check_errors(observations)
        
        # Rule 4: Critical Correlations
        self._check_correlations(correlations)
        
        # Rule 5: Overall Status Critical
        self._check_overall_status(analysis_report)
        
        return self.triggers_fired
    
    # =========================================================
    # RULE 1: Status Change
    # =========================================================
    
    def _check_status_change(self, changes: dict):
        """Check for status changes"""
        for source, change_report in changes.items():
            if not change_report.get("changed"):
                continue
            
            changes_detail = change_report.get("changes", {})
            if "status" not in changes_detail:
                continue
            
            status_change = changes_detail["status"]
            severity = status_change.get("severity", "info")
            old_val = status_change.get("from")
            new_val = status_change.get("to")
            
            # Severity Mapping
            if severity == "critical":
                trigger_sev = self.CRITICAL
            elif severity == "recovery":
                trigger_sev = self.LOW
            else:
                trigger_sev = self.MEDIUM
            
            self.triggers_fired.append({
                "type": "status_change",
                "source": source,
                "severity": trigger_sev,
                "message": f"{source} status: {old_val} → {new_val}",
                "context": {
                    "from": old_val,
                    "to": new_val,
                    "change_severity": severity
                }
            })
    
    # =========================================================
    # RULE 2: Confidence Drop
    # =========================================================
    
    def _check_confidence_drop(self, observations: dict, threshold: int = 15):
        """Check for confidence drops"""
        for source, obs in observations.items():
            if not obs:
                continue
            
            change = obs.get("change_report", {})
            if not change.get("changed"):
                continue
            
            changes_detail = change.get("changes", {})
            if "confidence" not in changes_detail:
                continue
            
            conf_change = changes_detail["confidence"]
            old_conf = conf_change.get("from", 0)
            new_conf = conf_change.get("to", 0)
            
            try:
                drop = int(old_conf) - int(new_conf)
            except (ValueError, TypeError):
                continue
            
            if drop >= threshold:
                severity = self.HIGH if drop >= 30 else self.MEDIUM
                self.triggers_fired.append({
                    "type": "confidence_drop",
                    "source": source,
                    "severity": severity,
                    "message": f"{source} confidence dropped: {old_conf}% → {new_conf}%",
                    "context": {
                        "drop": drop,
                        "old": old_conf,
                        "new": new_conf
                    }
                })
    
    # =========================================================
    # RULE 3: Error Appears
    # =========================================================
    
    def _check_errors(self, observations: dict):
        """Check for new errors"""
        for source, obs in observations.items():
            if not obs:
                continue
            
            if obs.get("error_type"):
                self.triggers_fired.append({
                    "type": "error_appeared",
                    "source": source,
                    "severity": self.CRITICAL,
                    "message": f"{source} is reporting error: {obs['error_type']}",
                    "context": {
                        "error_type": obs["error_type"],
                        "status": obs.get("status")
                    }
                })
    
    # =========================================================
    # RULE 4: Critical Correlations
    # =========================================================
    
    def _check_correlations(self, correlations: list):
        """Check for important correlations"""
        for corr in correlations:
            sev = corr.get("severity", "info")
            
            if sev in ["critical", "warning"]:
                trigger_sev = self.CRITICAL if sev == "critical" else self.HIGH
                self.triggers_fired.append({
                    "type": "correlation_alert",
                    "source": "correlation",
                    "severity": trigger_sev,
                    "message": corr["insight"],
                    "context": {
                        "action": corr["action"],
                        "confidence": corr["confidence"],
                        "pattern": corr.get("pattern")
                    }
                })
    
    # =========================================================
    # RULE 5: Overall Status Critical
    # =========================================================
    
    def _check_overall_status(self, report: dict):
        """Check overall status"""
        status = report.get("overall_status", "unknown")
        conf = report.get("overall_confidence", 0)
        
        if status == "critical":
            self.triggers_fired.append({
                "type": "overall_critical",
                "source": "system",
                "severity": self.CRITICAL,
                "message": f"System Status: CRITICAL (confidence: {conf}%)",
                "context": {"overall_status": status}
            })
        elif status == "warning" and conf >= 80:
            self.triggers_fired.append({
                "type": "overall_warning",
                "source": "system",
                "severity": self.MEDIUM,
                "message": f"System Status: WARNING (confidence: {conf}%)",
                "context": {"overall_status": status}
            })
    
    # =========================================================
    # HELPER
    # =========================================================
    
    def has_critical(self) -> bool:
        """Is there a critical trigger?"""
        return any(t["severity"] == self.CRITICAL for t in self.triggers_fired)
    
    def summary(self) -> str:
        """Summary of triggers"""
        if not self.triggers_fired:
            return "No triggers fired."
        
        lines = [f"🚨 {len(self.triggers_fired)} trigger(s) fired:"]
        for t in self.triggers_fired:
            icon = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "⚡",
                "low": "ℹ️"
            }.get(t["severity"], "•")
            lines.append(f"   {icon} [{t['severity'].upper()}] {t['message']}")
        return "\n".join(lines)


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Testing Trigger Engine")
    print("=" * 60)
    
    # Simulated report
    test_report = {
        "overall_status": "critical",
        "overall_confidence": 92,
        "observations": {
            "backend": {
                "status": "down",
                "confidence": 60,
                "error_type": "network_timeout",
                "change_report": {
                    "changed": True,
                    "changes": {
                        "status": {
                            "from": "healthy", "to": "down",
                            "severity": "critical"
                        },
                        "confidence": {
                            "from": 98, "to": 60,
                            "severity": "critical"
                        }
                    }
                }
            },
            "repo": {
                "status": "clean",
                "confidence": 95,
                "error_type": None,
                "change_report": {"changed": False, "changes": {}}
            }
        },
        "changes": {},
        "correlations": [
            {
                "insight": "Backend is down, but the code is clean",
                "action": "Check Railway logs",
                "severity": "critical",
                "confidence": 85,
                "pattern": "backend:down + repo:clean"
            }
        ]
    }
    
    engine = TriggerEngine()
    triggers = engine.evaluate(test_report)
    
    print()
    print(engine.summary())
    print()
    print(f"Has critical: {engine.has_critical()}")
    print(f"\n✅ Trigger Engine test complete.")

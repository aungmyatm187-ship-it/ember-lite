"""
Ember Perception Layer
Combines everything and provides a single entry point

Usage:
    from perception.layer import perceive
    
    report = perceive()
    print(report['overall_status'])
"""

from datetime import datetime
from perception.observers import get_all_observers
from perception.analysis import AnalysisEngine
from perception.database import init_db, save_observation


class PerceptionLayer:
    """
    Ember's perception system
    Observers → Database → Analysis → Report
    """
    
    def __init__(self, observer_filter=None):
        """
        Args:
            observer_filter: List of observer names (None = all)
        """
        init_db()
        self.observers = get_all_observers()
        
        # Apply filter
        if observer_filter:
            self.observers = [
                o for o in self.observers if o.name in observer_filter
            ]
        
        self.analysis_engine = AnalysisEngine()
    
    def perceive(self, save=True) -> dict:
        """
        Collect observations and run analysis
        
        Args:
            save: whether to save to the database
        
        Returns: Full perception report
        """
        report = {
            "perceived_at": datetime.now().isoformat(),
            "observer_count": len(self.observers),
            "observations": {},
            "errors": [],
            "analysis": {}
        }
        
        # 1. Collect observations
        for observer in self.observers:
            try:
                obs = observer.observe()
                report["observations"][observer.name] = obs
                
                if save:
                    save_observation(obs)
            except Exception as e:
                report["errors"].append({
                    "observer": observer.name,
                    "error": str(e)
                })
        
        # 2. Run analysis
        report["analysis"] = self.analysis_engine.analyze(
            report["observations"]
        )
        
        return report
    
    def quick_perceive(self) -> dict:
        """
        Fast perceive without saving
        """
        return self.perceive(save=False)


# =========================================================
# MODULE-LEVEL FUNCTIONS (Easy Import)
# =========================================================

def perceive(observer_filter=None, save=True) -> dict:
    """
    Ask Ember to observe
    
    Args:
        observer_filter: e.g. ["backend", "repo"]
        save: whether to save to the database
    
    Returns: perception report
    """
    layer = PerceptionLayer(observer_filter=observer_filter)
    return layer.perceive(save=save)


def perceive_summary(report: dict) -> str:
    """
    Convert report into a human-readable summary
    """
    analysis = report.get("analysis", {})
    observations = report.get("observations", {})
    
    lines = []
    lines.append("=" * 60)
    lines.append("  EMBER PERCEPTION REPORT")
    lines.append("=" * 60)
    lines.append("")
    
    # Overall
    status = analysis.get("overall_status", "unknown").upper()
    conf = analysis.get("overall_confidence", 0)
    
    status_icon = {
        "HEALTHY": "✅",
        "ATTENTION": "⚠️",
        "WARNING": "⚠️",
        "CRITICAL": "🚨"
    }.get(status, "❓")
    
    lines.append(f"{status_icon} Overall Status:  {status}")
    lines.append(f"🎯 Overall Confidence: {conf}%")
    lines.append("")
    
    # Observations
    lines.append("📊 Observations:")
    for source, obs in observations.items():
        if not obs:
            continue
        sc = obs.get("scored_confidence", obs.get("confidence", 0))
        cost = obs.get("cost_ms", 0)
        lines.append(
            f"   • {source:12} → {obs['status']:15} "
            f"(conf: {sc}%, cost: {cost}ms)"
        )
    lines.append("")
    
    # Changes
    changes = analysis.get("changes", {})
    changed_any = any(c.get("changed") for c in changes.values())
    
    lines.append("🔄 Changes:")
    if changed_any:
        for source, change in changes.items():
            if change.get("changed"):
                for field, c in change["changes"].items():
                    lines.append(
                        f"   • {source}.{field}: "
                        f"{c['from']} → {c['to']} [{c['severity']}]"
                    )
    else:
        lines.append("   • No significant changes")
    lines.append("")
    
    # Correlations
    correlations = analysis.get("correlations", [])
    lines.append("🔗 Correlations:")
    if correlations:
        for corr in correlations:
            icon = {
                "success": "✅",
                "info": "ℹ️",
                "warning": "⚠️",
                "critical": "🚨"
            }.get(corr["severity"], "•")
            lines.append(f"   {icon} {corr['insight']}")
            lines.append(
                f"      → {corr['action']} "
                f"(conf: {corr['confidence']}%)"
            )
    else:
        lines.append("   • No correlations detected")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


if __name__ == "__main__":
    print("=" * 60)
    print("  Testing Perception Layer")
    print("=" * 60)
    print()
    
    # Full perception
    print("📡 Running full perception...")
    report = perceive()
    
    print()
    print(perceive_summary(report))
    
    print(f"\n✅ Perception complete in {report['perceived_at']}")

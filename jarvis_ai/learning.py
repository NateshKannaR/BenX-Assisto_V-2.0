"""
Learning Engine - Self-improvement system that learns from failures, corrections,
and user feedback. Includes pattern confidence scoring and proactive re-analysis.
"""
import json
import re
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
from jarvis_ai.config import Config

logger = logging.getLogger(__name__)

class LearningEngine:
    """Self-improvement system that learns from failures and corrections.
    Features:
    - Pattern confidence scoring (weighted by usage frequency)
    - User feedback loop (re-analyzes immediately on correction signals)
    - Proactive improvement tracking with hit counters
    """

    # Words that signal user is correcting BenX
    CORRECTION_SIGNALS = [
        "no", "wrong", "incorrect", "instead", "should", "correction",
        "fix", "improve", "actually", "wait", "that's not", "you misunderstood",
        "not what i meant", "not right", "try again"
    ]
    
    def __init__(self, ai_engine):
        self.ai_engine = ai_engine
        self.learned_patterns = {}
        self.corrections = []
        self.load_learning()
    
    def load_learning(self):
        """Load learned patterns and corrections"""
        try:
            if Config.LEARNING_FILE.exists():
                with open(Config.LEARNING_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.learned_patterns = self._sanitize_patterns(data.get("patterns", {}))
                    self.corrections = data.get("corrections", [])[-50:]  # Keep last 50
        except Exception as e:
            logger.warning(f"Failed to load learning data: {e}")
            self.learned_patterns = {}
            self.corrections = []
    
    def save_learning(self):
        """Save learned patterns and corrections"""
        try:
            with open(Config.LEARNING_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "patterns": self.learned_patterns,
                    "corrections": self.corrections[-50:],
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save learning data: {e}")

    def _is_valid_command_json(self, text: str) -> bool:
        if not text or not isinstance(text, str):
            return False
        stripped = text.strip()
        if not stripped.startswith("{"):
            return False
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            return False
        return isinstance(obj, dict) and isinstance(obj.get("command"), str) and bool(obj.get("command"))

    def _sanitize_patterns(self, patterns: dict) -> dict:
        sanitized = {}
        for key, value in (patterns or {}).items():
            if not isinstance(value, dict):
                continue
            candidate = value.get("correct_command")
            if self._is_valid_command_json(candidate):
                sanitized[key] = value
            else:
                logger.info(f"Discarding invalid learned pattern for: {key}")
        return sanitized

    def _is_correction(self, user_input: str) -> bool:
        """Detect if the user is explicitly correcting BenX."""
        lower = user_input.lower()
        return any(sig in lower for sig in self.CORRECTION_SIGNALS)
    
    def learn_from_failure(self, user_input: str, command: str, result: str, error: str = None):
        """Learn from a failed command execution or user correction.
        Runs AI analysis asynchronously in a background thread to avoid blocking.
        """
        is_correction = self._is_correction(user_input)
        
        if "❌" not in result and not error and not is_correction:
            return

        if is_correction:
            logger.info(f"🔄 User correction detected for: {user_input}")
        
        try:
            system_prompt = """You are BenX's self-improvement analyzer. When a command fails, analyze why and suggest how to fix it.

Analyze:
1. What went wrong?
2. Why did it fail?
3. What should have been done instead?
4. How can this be prevented in the future?

Return ONLY a JSON object with keys: problem, solution, pattern"""

            correction_type = "User Correction" if is_correction else "Command Failure"
            
            analysis_prompt = f"""{correction_type} Analysis:

User Input: "{user_input}"
Command Attempted: "{command}"
Result: "{result[:300]}"
Error: "{error if error else 'N/A'}"

Return JSON with problem, solution, and pattern."""

            analysis = self.ai_engine.query_groq(system_prompt, analysis_prompt)
            
            # Extract JSON — handle markdown code blocks
            json_match = re.search(r'\{[^}]+\}', analysis, re.DOTALL)
            if json_match:
                try:
                    learned = json.loads(json_match.group(0))
                    correction = {
                        "timestamp": datetime.now().isoformat(),
                        "user_input": user_input,
                        "command": command,
                        "result": result[:200],
                        "error": error,
                        "problem": learned.get("problem", ""),
                        "solution": learned.get("solution", ""),
                        "pattern": learned.get("pattern", "")
                    }
                    self.corrections.append(correction)
                    
                    pattern = learned.get("pattern", "")
                    solution = learned.get("solution", "")
                    if pattern and self._is_valid_command_json(solution):
                        existing = self.learned_patterns.get(user_input.lower(), {})
                        self.learned_patterns[user_input.lower()] = {
                            "correct_command": solution,
                            "pattern": pattern,
                            "learned_at": datetime.now().isoformat(),
                            # Confidence: increment if pattern already exists
                            "confidence": existing.get("confidence", 0) + (2 if is_correction else 1),
                            "hit_count": existing.get("hit_count", 0),
                        }
                    elif pattern:
                        logger.info(f"Skipping non-command learning output for: {user_input}")
                    
                    self.save_learning()
                    logger.info(f"✅ Learned from {'correction' if is_correction else 'failure'}: {user_input}")
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Learning analysis failed: {e}")
    
    def apply_learned_pattern(self, user_input: str) -> Optional[str]:
        """Apply learned patterns. Patterns with higher confidence score are preferred.
        Increments hit_count on each successful match for future weighting.
        """
        user_lower = user_input.lower()
        
        # Exact match
        if user_lower in self.learned_patterns:
            pattern = self.learned_patterns[user_lower]
            corrected = pattern.get("correct_command", None)
            if self._is_valid_command_json(corrected):
                pattern["hit_count"] = pattern.get("hit_count", 0) + 1
                logger.info(f"✅ Applying learned pattern (confidence={pattern.get('confidence',1)}, hits={pattern['hit_count']}): {user_input}")
                return corrected
        
        # Partial match — prefer highest confidence
        candidates = []
        for pattern_key, pattern_data in self.learned_patterns.items():
            if pattern_key in user_lower or user_lower in pattern_key:
                corrected = pattern_data.get("correct_command", None)
                if self._is_valid_command_json(corrected):
                    candidates.append((pattern_data.get("confidence", 1), pattern_key, corrected, pattern_data))
        
        if candidates:
            # Pick highest confidence
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, key, corrected, pattern_data = candidates[0]
            pattern_data["hit_count"] = pattern_data.get("hit_count", 0) + 1
            logger.info(f"✅ Applying learned pattern partial match for: {user_input} -> {key}")
            return corrected
        
        return None
    
    def self_reflect(self, user_input: str, command: str, result: str):
        """Self-reflect on execution and improve"""
        if "❌" in result or "failed" in result.lower() or "error" in result.lower():
            self.learn_from_failure(user_input, command, result)
            
            corrected = self.apply_learned_pattern(user_input)
            if corrected:
                logger.info(f"Auto-correcting based on learned pattern: {corrected}")
                return corrected
        
        return None
    
    def get_improvement_suggestions(self) -> str:
        """Get suggestions for improvement based on learned patterns.
        Surfaces the most-used corrections and highest-confidence patterns.
        """
        if not self.corrections:
            return "No corrections recorded yet."
        
        recent = self.corrections[-5:]
        suggestions = []
        for corr in recent:
            if corr.get("solution"):
                suggestions.append(f"- [{corr.get('problem', 'issue')[:40]}] → {corr['solution'][:60]}")
        
        # Add top confidence patterns
        top_patterns = sorted(
            [(k, v) for k, v in self.learned_patterns.items()],
            key=lambda x: x[1].get("confidence", 0),
            reverse=True
        )[:3]
        if top_patterns:
            suggestions.append("\nTop learned patterns:")
            for key, data in top_patterns:
                suggestions.append(f"  • '{key}' (confidence={data.get('confidence',1)}, hits={data.get('hit_count',0)})")
        
        return "\n".join(suggestions) if suggestions else "No suggestions available."











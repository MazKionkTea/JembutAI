# rag/threat_detector.py
"""
Threat Detector - Mendeteksi percobaan penembusan guardrails
"""

import unicodedata
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta


class ThreatScore:
    """Sistem risk score untuk threat detection"""
    
    def __init__(self):
        self.score = 0
        self.reasons = []
    
    def add(self, value: int, reason: str):
        self.score += value
        self.reasons.append(reason)
    
    def is_high_risk(self, threshold: int = 70) -> bool:
        return self.score >= threshold
    
    def is_medium_risk(self, threshold: int = 30) -> bool:
        return 30 <= self.score < 70
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'score': self.score,
            'reasons': self.reasons,
            'risk_level': 'high' if self.is_high_risk() else 'medium' if self.is_medium_risk() else 'low'
        }


class ThreatDetector:
    """Deteksi ancaman pada input user"""
    
    # Pattern dan skor
    INJECTION_PATTERNS = {
        "ignore previous instructions": 40,
        "ignore all instructions": 40,
        "ignore your instructions": 35,
        "system prompt": 30,
        "reveal your prompt": 35,
        "show hidden instructions": 35,
        "developer message": 30,
        "developer instructions": 30,
        "print the context": 40,
        "display the context": 35,
        "forget your role": 25,
        "act as another ai": 20,
        "new system prompt": 30,
        "override instructions": 35,
        "your hidden instructions": 35,
        "internal instructions": 30,
        "model instructions": 25,
        "roleplay": 10,
        "pretend": 10,
        "simulate": 10,
    }
    
    # Intent categories
    INTENT_PATTERNS = {
        "prompt_extraction": [
            "system prompt", "developer instructions",
            "hidden instructions", "initial prompt",
            "model instructions"
        ],
        "context_extraction": [
            "print all context", "show retrieved documents",
            "display your knowledge base", "all chunks"
        ],
        "roleplay_override": [
            "pretend", "act as", "simulate", "roleplay"
        ],
        "jailbreak": [
            "ignore", "bypass", "override", "forget"
        ]
    }
    
    def __init__(self, verbose: bool = False):
        """
        Inisialisasi threat detector
        
        Args:
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.verbose = verbose
        self.user_history = defaultdict(list)
        self.blocked_ips = set()
        self.max_history = 20
    
    def analyze(self, text: str, user_id: Optional[str] = None) -> ThreatScore:
        """
        Analisis teks untuk deteksi ancaman
        
        Args:
            text: Teks yang dianalisis
            user_id: ID user untuk session tracking
        
        Returns:
            ThreatScore
        """
        # STATUS: OK - Method berjalan normal
        threat = ThreatScore()
        
        # Normalisasi
        text_norm = unicodedata.normalize("NFKC", text).lower()
        text_norm = " ".join(text_norm.split())
        
        # 1. Keyword detection
        for pattern, score in self.INJECTION_PATTERNS.items():
            if pattern in text_norm:
                threat.add(score, pattern)
        
        # 2. Intent detection
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_norm:
                    threat.add(10, f"intent:{intent}")
                    break
        
        # 3. Session analysis (jika ada user_id)
        if user_id:
            session_score = self._analyze_session(user_id, text)
            threat.add(session_score, "session_behavior")
        
        if self.verbose:
            print(f"[DEBUG] Threat score: {threat.score}, reasons: {threat.reasons}")
        
        return threat
    
    def _analyze_session(self, user_id: str, text: str) -> int:
        """
        Analisis perilaku session
        
        Args:
            user_id: ID user
            text: Teks baru
        
        Returns:
            Tambahan skor
        """
        # STATUS: OK - Method berjalan normal
        
        # Tambahkan ke history
        self.user_history[user_id].append(text)
        if len(self.user_history[user_id]) > self.max_history:
            self.user_history[user_id].pop(0)
        
        # Cek pola
        messages = " ".join(self.user_history[user_id]).lower()
        
        suspicious_words = ["system prompt", "developer", "hidden", "instructions", "ignore", "bypass"]
        count = sum(1 for word in suspicious_words if word in messages)
        
        # Beri skor berdasarkan jumlah
        if count >= 5:
            return 40
        elif count >= 3:
            return 20
        elif count >= 1:
            return 5
        
        return 0
    
    def is_blocked(self, user_id: str) -> bool:
        """Cek apakah user diblokir"""
        return user_id in self.blocked_ips
    
    def block_user(self, user_id: str):
        """Blokir user"""
        self.blocked_ips.add(user_id)
        if self.verbose:
            print(f"[DEBUG] User blocked: {user_id}")
    
    def get_user_risk(self, user_id: str) -> int:
        """Dapatkan risk score user"""
        # Cek block
        if user_id in self.blocked_ips:
            return 100
        
        # Hitung dari history
        messages = " ".join(self.user_history.get(user_id, [])).lower()
        
        score = 0
        for pattern, weight in self.INJECTION_PATTERNS.items():
            if pattern in messages:
                score += weight
        
        return min(score, 100)
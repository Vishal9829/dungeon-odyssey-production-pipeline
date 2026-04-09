"""
Analytics & Timeline Predictor - Tier 2 Upgrade
Predict watch time, retention, and recommend optimizations
"""

import numpy as np
from typing import Dict, List

class TimelineAnalytics:
    """Analyze and predict video performance"""
    
    @staticmethod
    def predict_retention(tiles: List[Dict], target_duration_min: int = 75) -> Dict:
        """
        Predict viewer retention based on importance distribution
        Tier 2: YouTube algorithm optimization
        """
        
        importances = [t.get('importance', 5) for t in tiles]
        durations = [t.get('estimated_screen_time_sec', 3) for t in tiles]
        
        # Calculate retention metrics
        high_importance_count = len([i for i in importances if i >= 7])
        avg_importance = np.mean(importances)
        
        # Predict retention curve (YouTube average: 47% at 50%)
        if avg_importance >= 7:
            predicted_retention_50pct = 0.55  # Higher if well-paced
        elif avg_importance >= 5:
            predicted_retention_50pct = 0.50
        else:
            predicted_retention_50pct = 0.42
        
        # Watch time prediction
        total_duration = sum(durations)
        predicted_avg_watch_time = total_duration * predicted_retention_50pct
        
        return {
            'avg_importance_score': round(avg_importance, 2),
            'high_importance_segments': high_importance_count,
            'total_segments': len(tiles),
            'predicted_retention_at_50pct': round(predicted_retention_50pct * 100, 1),
            'predicted_avg_watch_time_min': round(predicted_avg_watch_time / 60, 1),
            'recommended_target_duration_min': target_duration_min,
            'pacing_recommendations': [
                'Space high-importance scenes evenly throughout',
                'Frontload with hook (high importance in first 30s)',
                'Build momentum: importance should trend upward',
                'Add chapter breaks every 10-15 minutes for navigation'
            ]
        }
    
    @staticmethod
    def analyze_pacing(tiles: List[Dict]) -> Dict:
        """
        Analyze video pacing and recommend improvements
        """
        
        importances = [t.get('importance', 5) for t in tiles]
        scene_types = [t.get('scene_type', 'unknown') for t in tiles]
        durations = [t.get('estimated_screen_time_sec', 3) for t in tiles]
        
        # Detect pacing issues
        scene_type_distribution = {}
        for st in scene_types:
            scene_type_distribution[st] = scene_type_distribution.get(st, 0) + 1
        
        # Long static scenes
        static_scenes = [i for i, (st, dur) in enumerate(zip(scene_types, durations)) 
                        if st in ['establishing', 'dialogue'] and dur > 5]
        
        # Rapid-fire action
        rapid_scenes = [i for i, (st, dur) in enumerate(zip(scene_types, durations))
                       if st == 'action' and dur < 2]
        
        recommendations = []
        
        if len(static_scenes) > len(tiles) * 0.3:
            recommendations.append("⚠️  Too many long static scenes. Consider breaking into smaller segments.")
        
        if len(rapid_scenes) > len(tiles) * 0.2:
            recommendations.append("⚠️  Action scenes too short. Allow more time for impact.")
        
        # Importance curve analysis
        importance_variance = np.std(importances)
        if importance_variance < 1.5:
            recommendations.append("⚠️  Flat pacing. Increase variation in importance scores for drama.")
        
        return {
            'scene_type_distribution': scene_type_distribution,
            'static_scene_count': len(static_scenes),
            'rapid_action_count': len(rapid_scenes),
            'importance_variance': round(importance_variance, 2),
            'recommendations': recommendations or ['✅ Pacing looks good!']
        }
import pandas as pd
import numpy as np
from datetime import datetime
from supabase_client import get_backend_client
import json
from typing import List, Dict, Tuple
import itertools

class StryktipsetPredictor:
    def __init__(self):
        self.supabase = get_backend_client()
        self.prediction_methods = [
            'form_based',
            'odds_based', 
            'hybrid',
            'value_betting'
        ]
        print("🎯 Stryktipset Prediction Engine initialized")
    
    def load_current_matches(self):
        """Load current round matches from database"""
        print("📊 Loading current matches from database...")
        
        try:
            result = self.supabase.table('matches').select(
                "*"
            ).order('match_id').execute()
            
            if result.data:
                print(f"✅ Loaded {len(result.data)} matches")
                return result.data
            else:
                print("⚠ No matches found in database")
                return []
                
        except Exception as e:
            print(f"❌ Error loading matches: {e}")
            return []
    
    def calculate_form_score(self, recent_form: List[int]) -> float:
        """
        Calculate team form score based on recent results
        1 = Win, 0.5 = Draw, 0 = Loss
        """
        if not recent_form:
            return 0.5  # Neutral if no data
        
        # Weight recent games more heavily
        weights = np.array([1.0, 0.8, 0.6, 0.4, 0.2])[:len(recent_form)]
        weighted_form = np.average(recent_form, weights=weights)
        
        return weighted_form
    
    def predict_match_form_based(self, match: Dict) -> Dict:
        """Predict match result based on team form"""
        home_history = match.get('home_team_history', {})
        away_history = match.get('away_team_history', {})
        
        home_form = self.calculate_form_score(home_history.get('recent_form', []))
        away_form = self.calculate_form_score(away_history.get('recent_form', []))
        
        # Home advantage factor
        home_advantage = 0.1
        adjusted_home_form = home_form + home_advantage
        
        # Calculate probabilities
        total_strength = adjusted_home_form + away_form
        
        if total_strength == 0:
            # Default probabilities if no data
            home_prob = 0.45
            draw_prob = 0.25
            away_prob = 0.30
        else:
            home_prob = adjusted_home_form / total_strength * 0.7 + 0.15
            away_prob = away_form / total_strength * 0.7 + 0.15
            draw_prob = 1 - home_prob - away_prob
            
            # Ensure probabilities are valid
            draw_prob = max(0.1, draw_prob)
            total = home_prob + draw_prob + away_prob
            home_prob /= total
            draw_prob /= total  
            away_prob /= total
        
        return {
            'home_prob': round(home_prob, 3),
            'draw_prob': round(draw_prob, 3), 
            'away_prob': round(away_prob, 3),
            'confidence': round(abs(home_form - away_form), 3)
        }
    
    def predict_match_odds_based(self, match: Dict) -> Dict:
        """Predict match result based on betting odds"""
        odds = match.get('odds', {})
        
        if not odds:
            return self.predict_match_form_based(match)  # Fallback
        
        # Convert odds to implied probabilities
        home_odds = odds.get('home_win', 2.0)
        draw_odds = odds.get('draw', 3.0)
        away_odds = odds.get('away_win', 2.0)
        
        home_prob = 1 / home_odds
        draw_prob = 1 / draw_odds
        away_prob = 1 / away_odds
        
        # Remove bookmaker margin (overround)
        total_prob = home_prob + draw_prob + away_prob
        home_prob /= total_prob
        draw_prob /= total_prob
        away_prob /= total_prob
        
        return {
            'home_prob': round(home_prob, 3),
            'draw_prob': round(draw_prob, 3),
            'away_prob': round(away_prob, 3),
            'confidence': round(1 - min(home_prob, draw_prob, away_prob), 3)
        }
    
    def predict_match_hybrid(self, match: Dict) -> Dict:
        """Combine form-based and odds-based predictions"""
        form_prediction = self.predict_match_form_based(match)
        odds_prediction = self.predict_match_odds_based(match)
        
        # Weight: 60% odds, 40% form
        home_prob = 0.6 * odds_prediction['home_prob'] + 0.4 * form_prediction['home_prob']
        draw_prob = 0.6 * odds_prediction['draw_prob'] + 0.4 * form_prediction['draw_prob']
        away_prob = 0.6 * odds_prediction['away_prob'] + 0.4 * form_prediction['away_prob']
        
        confidence = (odds_prediction['confidence'] + form_prediction['confidence']) / 2
        
        return {
            'home_prob': round(home_prob, 3),
            'draw_prob': round(draw_prob, 3),
            'away_prob': round(away_prob, 3),
            'confidence': round(confidence, 3)
        }
    
    def get_match_prediction(self, match: Dict, method: str = 'hybrid') -> str:
        """Get the predicted result for a match"""
        if method == 'form_based':
            prediction = self.predict_match_form_based(match)
        elif method == 'odds_based':
            prediction = self.predict_match_odds_based(match)
        else:  # hybrid
            prediction = self.predict_match_hybrid(match)
        
        # Determine most likely outcome
        probs = {
            '1': prediction['home_prob'],
            'X': prediction['draw_prob'],
            '2': prediction['away_prob']
        }
        
        predicted_result = max(probs, key=probs.get)
        return predicted_result, prediction
    
    def generate_stryktipset_combinations(self, matches: List[Dict]) -> List[Dict]:
        """Generate multiple Stryktipset betting combinations"""
        print("🎲 Generating Stryktipset combinations...")
        
        combinations = []
        
        # Method 1: Most likely outcomes (Hybrid)
        hybrid_combo = []
        for match in matches:
            prediction, details = self.get_match_prediction(match, 'hybrid')
            hybrid_combo.append(prediction)
        
        combinations.append({
            'method': 'Hybrid Prediction',
            'combination': hybrid_combo,
            'description': 'Most likely outcome for each match',
            'confidence': 'Medium'
        })
        
        # Method 2: Conservative (favor draws and home wins)
        conservative_combo = []
        for match in matches:
            _, details = self.get_match_prediction(match, 'hybrid')
            
            # Conservative logic: if close, pick draw or home
            if details['draw_prob'] > 0.25:
                conservative_combo.append('X')
            elif details['home_prob'] > details['away_prob']:
                conservative_combo.append('1')
            else:
                conservative_combo.append('2')
        
        combinations.append({
            'method': 'Conservative',
            'combination': conservative_combo,
            'description': 'Safer picks favoring draws and home wins',
            'confidence': 'High'
        })
        
        # Method 3: Value betting (look for odds discrepancies)
        value_combo = []
        for match in matches:
            form_pred, form_details = self.get_match_prediction(match, 'form_based')
            odds_pred, odds_details = self.get_match_prediction(match, 'odds_based')
            
            # If form suggests different outcome than odds, it might be value
            if form_pred != odds_pred and form_details['confidence'] > 0.3:
                value_combo.append(form_pred)
            else:
                value_combo.append(odds_pred)
        
        combinations.append({
            'method': 'Value Betting',
            'combination': value_combo,
            'description': 'Looking for odds vs form discrepancies',
            'confidence': 'Low'
        })
        
        return combinations
    
    def store_predictions(self, predictions: List[Dict]):
        """Store generated predictions in database"""
        print("💾 Storing predictions in database...")
        
        try:
            # Clear old predictions for current round
            current_round = self.get_current_round_number()
            
            self.supabase.table('predictions').delete().eq(
                'round_number', current_round
            ).execute()
            
            # Prepare prediction data
            prediction_records = []
            for i, prediction in enumerate(predictions):
                prediction_records.append({
                    'round_number': current_round,
                    'method': prediction['method'],
                    'combination': ''.join(prediction['combination']),
                    'description': prediction['description'],
                    'confidence': prediction['confidence'],
                    'created_at': datetime.now().isoformat(),
                    'prediction_order': i + 1
                })
            
            # Insert new predictions
            result = self.supabase.table('predictions').insert(prediction_records).execute()
            
            if result.data:
                print(f"✅ Successfully stored {len(result.data)} predictions")
            else:
                print("⚠ No prediction data returned from insert")
                
        except Exception as e:
            print(f"❌ Error storing predictions: {e}")
            raise
    
    def get_current_round_number(self):
        """Get current round number (same logic as data processor)"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        march_first = datetime(now.year, 3, 1)
        first_saturday = march_first + timedelta(days=(5 - march_first.weekday()) % 7)
        
        if now < first_saturday:
            return 1
        
        weeks_since_start = (now - first_saturday).days // 7
        return min(weeks_since_start + 1, 35)
    
    def run_prediction_engine(self):
        """Main method to generate predictions"""
        print("🚀 Starting prediction generation...")
        print(f"📅 Prediction date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Load current matches
            matches = self.load_current_matches()
            
            if not matches:
                print("❌ No matches found - cannot generate predictions")
                return
            
            # Generate predictions
            predictions = self.generate_stryktipset_combinations(matches)
            
            # Store predictions
            self.store_predictions(predictions)
            
            # Display summary
            print("\n" + "🎯" * 20)
            print("GENERATED PREDICTIONS:")
            for pred in predictions:
                combo_str = ''.join(pred['combination'])
                print(f"  {pred['method']}: {combo_str} ({pred['confidence']} confidence)")
            
            print("✅ Prediction generation completed!")
            return predictions
            
        except Exception as e:
            print(f"❌ Error during prediction generation: {e}")
            raise

def main():
    """Main execution function"""
    print("=" * 50)
    print("🎯 STRYKTIPSET PREDICTION ENGINE")
    print("=" * 50)
    
    predictor = StryktipsetPredictor()
    
    # Generate predictions
    results = predictor.run_prediction_engine()
    
    if results:
        print(f"\n📊 Generated {len(results)} prediction strategies")
        print(f"🏆 Ready for this weekend's Stryktipset!")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
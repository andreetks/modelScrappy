from pysentimiento import create_analyzer
import torch

class ReviewAnalyzer:
    """
    NLP Engine using Pysentimiento (Transformers) for Spanish Sentiment Analysis.
    """
    def __init__(self):
        print("🧠 Loading NLP Model (pysentimiento/robertuito)...")
        # Use GPU if available, else CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.analyzer = create_analyzer(task="sentiment", lang="es")
        print(f"✅ Model loaded on {self.device}")

    def analyze(self, reviews):
        """
        Analyzes a list of reviews.
        Adds 'sentiment' and 'confidence' keys to each review dict.
        """
        results = []
        summary = {"POS": 0, "NEG": 0, "NEU": 0}
        total_rating = 0
        valid_ratings = 0

        print(f"🔍 Analyzing {len(reviews)} reviews...")
        
        for r in reviews:
            text = r.get("review_text", "")
            
            # Simple metadata calculation
            if r.get("rating"):
                total_rating += float(r["rating"])
                valid_ratings += 1

            # NLP Prediction
            if text and len(text) > 2:
                try:
                    prediction = self.analyzer.predict(text)
                    sentiment = prediction.output # POS, NEG, NEU
                    score = max(prediction.probas.values())
                    
                    r["sentiment"] = sentiment
                    r["confidence"] = round(score, 4)
                    
                    if sentiment in summary:
                        summary[sentiment] += 1
                except Exception as e:
                    print(f"⚠️ NLP Error on text: {text[:20]}... {e}")
                    r["sentiment"] = "ERROR"
                    r["confidence"] = 0.0
            else:
                r["sentiment"] = "NEU" # Empty text usually neutral
                r["confidence"] = 1.0
                summary["NEU"] += 1
            
            results.append(r)

        avg_rating = round(total_rating / valid_ratings, 2) if valid_ratings > 0 else 0
        
        return {
            "reviews": results,
            "sentiment_summary": summary,
            "average_rating": avg_rating,
            "total_reviews": len(reviews)
        }

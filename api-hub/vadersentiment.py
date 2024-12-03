
from pydantic import BaseModel
from typing import List, Dict
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


analyzer = SentimentIntensityAnalyzer()

class TextInput(BaseModel):
    texts: List[str]

async def analyze_sentiment(input: TextInput) -> List[Dict[str, float]]:
    results = []
    for text in input.texts:
        scores = analyzer.polarity_scores(text)
        results.append({
            "text": text,
            "compound": scores["compound"],
            "positive": scores["pos"],
            "neutral": scores["neu"],
            "negative": scores["neg"]
        })
    return results

from typing import Dict, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SentimentType(str, Enum):
    POSITIVE = 'positive'
    NEGATIVE = 'negative'
    NEUTRAL = 'neutral'

class SentimentService:
    """
    情感分析服务
    """
    NEGATIVE_WORDS = {
        '非常差': -1.0,
        '很差': -0.9,
        '差': -0.8,
        '不满意': -0.7,
        '失望': -0.7,
        '生气': -0.9,
        '愤怒': -1.0,
        '投诉': -0.8,
        '骗子': -1.0,
        '太差': -0.9,
        '糟糕': -0.8,
        '后悔': -0.6
    }

    POSITIVE_WORDS = {
        '很好': 0.9,
        '非常好': 1.0,
        '棒': 0.8,
        '满意': 0.7,
        '喜欢': 0.8,
        '感谢': 0.6,
        '谢谢': 0.5,
        '好评': 0.8,
        '推荐': 0.7,
        '划算': 0.6,
        '便宜': 0.5,
        '漂亮': 0.7
    }

    NEGATION_WORDS = {'不', '没', '无', '非', '别', '勿'}

    async def analyze(self, text: str) -> Tuple[SentimentType, float]:
        """
        分析文本情感
        """
        lexicon_score = self._lexicon_analysis(text)
        rule_score = self._rule_analysis(text)
        final_score = max(-1.0, min(1.0, lexicon_score * 0.7 + rule_score * 0.3))
        sentiment_type = self._score_to_type(final_score)
        return sentiment_type, final_score

    def _is_negated(self, text: str, word: str) -> bool:
        word_index = text.find(word)
        if word_index < 0:
            return False

        for neg in self.NEGATION_WORDS:
            neg_index = text.rfind(neg, 0, word_index)
            if neg_index >= 0 and 0 < word_index - neg_index < 5:
                    return True
        return False

    def _lexicon_analysis(self, text: str) -> float:
        """
        使用词典分析情感
        """

        total_score = 0.0
        word_count = 0

        for word, score in {**self.NEGATIVE_WORDS, **self.POSITIVE_WORDS}.items():
            if word in text:
                if self._is_negated(text, word):
                    total_score += score * -0.5
                else: 
                    total_score += score
                word_count += 1
        
        return total_score / word_count if word_count > 0 else 0.0

    def _rule_analysis(self, text: str) -> float:
        """
        使用规则分析情感
        """
        import re
        score = 0.0
        if re.findall(r'(.)\1{2,}', text):
            score += 0.1 if self._contains_positive_hint(text) else -0.1
        if text.isupper() and len(text) > 3:
            score -= 0.2
        exclamation_count = text.count('!') + text.count('！')
        if exclamation_count:
            score += 0.05 * exclamation_count if self._contains_positive_hint(text) else -0.05 * exclamation_count
        return score

    def _contains_positive_hint(self, text: str) -> bool:
        return any(word in text for word in self.POSITIVE_WORDS)

    def _score_to_type(self, score: float) -> SentimentType:
        """
        根据情感分数返回情感类型
        """
        if score <= -0.5:
            return SentimentType.NEGATIVE
        elif score > 0.5:
            return SentimentType.POSITIVE
        else:
            return SentimentType.NEUTRAL

    def get_response_strategy(self, sentiment: SentimentType, score: float) -> Dict:
        strategies = {
            SentimentType.POSITIVE: {
                'tone': 'friendly',
                'prefix': '很高兴为您服务',
                'action': '主动推荐关联服务',
                'priority': 'upsell'
            },
            SentimentType.NEGATIVE: {
                'tone': 'empathetic',
                'prefix': '很抱歉给您带来不愉快的体验',
                'action': '建议转人工服务',
                'priority': 'recover'
            },
            SentimentType.NEUTRAL: {
                'tone': 'professional',
                'prefix': '您好',
                'action': '正常服务流程',
                'priority': 'standard'
            }
        }
        strategy = strategies.get(sentiment, strategies[SentimentType.NEUTRAL]).copy()
        strategy['score'] = round(score, 3)
        return strategy

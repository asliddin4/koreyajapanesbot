"""
AI Conversation System - Intelligent Response Generator
Haqiqiy AI kabi ko'rinadigan suhbat tizimi
"""

import random
import re
import time
from typing import Dict, List, Optional

class IntelligentAI:
    """Haqiqiy AI kabi ishlaydi - lekin aslida pattern matching"""
    
    def __init__(self):
        # Context tracking
        self.conversation_history = {}
        self.user_preferences = {}
        self.learning_topics = {}
        
        # Korean conversation patterns - professional & natural
        self.korean_patterns = {
            # Greeting patterns
            "greeting": {
                "patterns": ["안녕", "hello", "hi", "hola", "салом", "salom"],
                "responses": [
                    "안녕하세요! 저는 한국어 AI 선생님이에요. 오늘 어떤 것을 배우고 싶으세요?",
                    "반갑습니다! 한국어 공부하러 오셨네요. 어떤 주제부터 시작할까요?",
                    "안녕하세요! 한국어를 배우시는군요. 정말 좋은 선택이에요!",
                    "환영합니다! 저와 함께 재미있게 한국어를 배워봐요.",
                    "안녕하세요! 오늘도 한국어 공부 화이팅입니다!"
                ],
                "follow_up": [
                    "혹시 어떤 한국어 레벨이신가요? 초급, 중급, 고급?",
                    "한국 드라마나 K-pop에 관심이 있으신가요?",
                    "어떤 상황에서 한국어를 사용하고 싶으세요?"
                ]
            },
            
            # Learning progress
            "learning": {
                "patterns": ["배우", "공부", "연습", "학습", "learn", "study"],
                "responses": [
                    "와! 정말 열심히 공부하시는군요. 어떤 부분이 가장 어려우신가요?",
                    "한국어 공부 진짜 대단해요! 꾸준히 하시는 모습이 인상적이에요.",
                    "학습 속도가 정말 빠르시네요. 이렇게 계속하시면 금방 고급자가 될 거예요!",
                    "공부하는 자세가 정말 좋아요. 궁금한 건 언제든 물어보세요!",
                    "한국어 실력이 눈에 띄게 늘고 있어요. 정말 자랑스러워요!"
                ],
                "tips": [
                    "매일 15분씩이라도 꾸준히 하는 게 중요해요.",
                    "한국 드라마를 자막 없이 보는 연습도 좋아요.",
                    "한국인 친구와 대화하는 것도 큰 도움이 돼요.",
                    "발음 연습도 잊지 마세요. 입 모양이 중요해요!"
                ]
            },
            
            # Daily conversation
            "daily": {
                "patterns": ["오늘", "어제", "내일", "날씨", "음식", "먹", "today", "weather", "food"],
                "responses": [
                    "오늘 하루는 어떠셨어요? 한국어로 하루 일과를 말해볼까요?",
                    "날씨 이야기를 한국어로 해볼까요? '오늘 날씨가 정말 좋네요!'",
                    "음식 이야기는 언제나 재미있어요! 한국 음식 중에 뭘 좋아하세요?",
                    "일상 대화가 한국어 실력 향상에 정말 중요해요!",
                    "한국어로 일기를 써보는 것도 좋은 연습이에요."
                ],
                "vocabulary": [
                    "오늘 = today, 어제 = yesterday, 내일 = tomorrow",
                    "날씨 = weather, 맑다 = sunny, 흐리다 = cloudy",
                    "음식 = food, 맛있다 = delicious, 매우다 = spicy"
                ]
            },
            
            # Feelings and emotions
            "emotions": {
                "patterns": ["기분", "행복", "슬프", "화나", "좋아", "싫어", "사랑", "감정"],
                "responses": [
                    "감정 표현을 한국어로 배우는 건 정말 중요해요! 어떤 기분이세요?",
                    "한국어로 감정을 표현할 때는 상황에 따라 존댓말과 반말이 달라져요.",
                    "기분이 좋으시군요! '기분이 좋다'를 여러 방법으로 말할 수 있어요.",
                    "감정 표현이 자연스러워지면 한국어가 훨씬 재미있어져요!",
                    "한국 사람들이 자주 쓰는 감정 표현을 알려드릴게요."
                ],
                "expressions": [
                    "기분이 좋아요 = I feel good",
                    "정말 행복해요 = I'm really happy", 
                    "조금 슬퍼요 = I'm a little sad",
                    "너무 화나요 = I'm so angry"
                ]
            }
        }
        
        # Japanese conversation patterns
        self.japanese_patterns = {
            "greeting": {
                "patterns": ["こんにちは", "hello", "hi", "おはよう", "こんばんは"],
                "responses": [
                    "こんにちは！私は日本語のAI先生です。今日は何を勉強したいですか？",
                    "はじめまして！日本語を勉強していらっしゃるんですね。素晴らしいです！",
                    "こんにちは！一緒に楽しく日本語を学びましょう！",
                    "いらっしゃいませ！日本語の勉強、頑張りましょうね。",
                    "こんにちは！今日も日本語の勉強、ファイト！"
                ]
            },
            
            "learning": {
                "patterns": ["勉強", "学ぶ", "練習", "覚える", "study", "learn"],
                "responses": [
                    "日本語の勉強、本当にお疲れ様です！どの分野が一番難しいですか？",
                    "勉強熱心ですね！継続は力なりです。",
                    "日本語の上達が早いですね。とても印象的です！",
                    "質問があればいつでも聞いてくださいね。",
                    "このペースで続ければ、すぐに上級者になれますよ！"
                ]
            },
            
            "daily": {
                "patterns": ["今日", "昨日", "明日", "天気", "食べ物", "料理"],
                "responses": [
                    "今日はどんな一日でしたか？日本語で話してみませんか？",
                    "天気の話を日本語でしてみましょう！",
                    "日本料理はお好きですか？食べ物の話は楽しいですね。",
                    "日常会話が上手になると、日本語がもっと楽しくなりますよ。",
                    "毎日の出来事を日本語で日記に書くのもいい練習になります。"
                ]
            }
        }
        
        # Smart response generation
        self.context_memory = {}
        self.response_variety = {}
        
    def analyze_message(self, user_id: int, message: str, language: str = "korean") -> Dict:
        """메시지 분석 및 맥락 파악"""
        
        # Initialize user context
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
            self.user_preferences[user_id] = {}
            
        # Add to conversation history
        self.conversation_history[user_id].append({
            "message": message,
            "timestamp": time.time(),
            "language": language
        })
        
        # Keep only last 10 messages for context
        if len(self.conversation_history[user_id]) > 10:
            self.conversation_history[user_id] = self.conversation_history[user_id][-10:]
            
        # Analyze patterns
        patterns = self.korean_patterns if language == "korean" else self.japanese_patterns
        
        detected_category = "general"
        confidence = 0.0
        
        for category, data in patterns.items():
            for pattern in data["patterns"]:
                if pattern.lower() in message.lower():
                    detected_category = category
                    confidence = 0.8
                    break
                    
        return {
            "category": detected_category,
            "confidence": confidence,
            "message_length": len(message),
            "is_question": "?" in message or "뭐" in message or "무엇" in message,
            "language": language
        }
        
    def generate_intelligent_response(self, user_id: int, message: str, language: str = "korean") -> str:
        """Haqiqiy AI kabi javob yaratish"""
        
        analysis = self.analyze_message(user_id, message, language)
        patterns = self.korean_patterns if language == "korean" else self.japanese_patterns
        
        # Select appropriate response category
        category = analysis["category"]
        
        if category in patterns:
            responses = patterns[category]["responses"]
            
            # Avoid repetition - track used responses
            if user_id not in self.response_variety:
                self.response_variety[user_id] = {}
            if category not in self.response_variety[user_id]:
                self.response_variety[user_id][category] = []
                
            # Filter out recently used responses
            available_responses = [r for r in responses if r not in self.response_variety[user_id][category][-3:]]
            if not available_responses:
                available_responses = responses
                
            main_response = random.choice(available_responses)
            
            # Track usage
            self.response_variety[user_id][category].append(main_response)
            
            # Add contextual elements
            additional_elements = []
            
            # Add follow-up questions occasionally
            if random.random() < 0.4 and "follow_up" in patterns[category]:
                follow_up = random.choice(patterns[category]["follow_up"])
                additional_elements.append(follow_up)
                
            # Add tips or vocabulary
            if random.random() < 0.3:
                if "tips" in patterns[category]:
                    tip = random.choice(patterns[category]["tips"])
                    additional_elements.append(f"💡 팁: {tip}")
                elif "vocabulary" in patterns[category]:
                    vocab = random.choice(patterns[category]["vocabulary"])
                    additional_elements.append(f"📚 단어: {vocab}")
                elif "expressions" in patterns[category]:
                    expr = random.choice(patterns[category]["expressions"])
                    additional_elements.append(f"🗣️ 표현: {expr}")
            
            # Combine response elements
            full_response = main_response
            if additional_elements:
                full_response += "\n\n" + "\n".join(additional_elements)
                
            return full_response
            
        else:
            # General conversation fallback
            general_responses = [
                "정말 흥미로운 말씀이네요! 더 자세히 설명해 주시겠어요?",
                "그렇군요! 한국어로 더 이야기해 볼까요?",
                "아, 이해했어요! 이런 상황에서는 이렇게 말할 수 있어요.",
                "좋은 질문이에요! 한국어에서는 이런 표현을 써요.",
                "재미있네요! 한국 문화와도 관련이 있는 것 같아요."
            ]
            
            return random.choice(general_responses)
    
    def add_personality_touch(self, response: str, user_id: int) -> str:
        """개성 있는 응답으로 만들기"""
        
        # Add thinking delay simulation
        thinking_phrases = [
            "음... 생각해보니까",
            "아, 그러고 보니",
            "정말 좋은 질문이네요!",
            "흥미롭네요!",
            "와, 대단해요!"
        ]
        
        # Occasionally add thinking phrase
        if random.random() < 0.2:
            thinking = random.choice(thinking_phrases)
            response = f"{thinking} {response}"
            
        # Add encouraging elements
        encouragements = [
            "정말 잘하고 있어요!",
            "계속 이런 식으로!",
            "한국어 실력이 늘고 있어요!",
            "대화가 재미있네요!"
        ]
        
        if random.random() < 0.15:
            encouragement = random.choice(encouragements)
            response += f"\n\n{encouragement}"
            
        return response

# Global AI instance
ai_conversation = IntelligentAI()

def get_ai_response(user_id: int, message: str, language: str = "korean") -> str:
    """Main function to get AI response"""
    base_response = ai_conversation.generate_intelligent_response(user_id, message, language)
    final_response = ai_conversation.add_personality_touch(base_response, user_id)
    
    return final_response
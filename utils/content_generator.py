import asyncio
import json
import logging
from typing import Dict, List, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class ContentGenerator:
    """
    Gemini API bilan professional content yaratish
    Pitch Deck va Prezentatsiya uchun
    """

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_pitch_deck_content(
            self,
            answers: List[str],
            use_gpt4: bool = True
    ) -> Dict:
        """
        Pitch Deck uchun professional content yaratish

        Args:
            answers: 10 ta savolga javoblar
            use_gpt4: GPT-4 ishlatish (yoki GPT-3.5)

        Returns:
            Professional pitch content (JSON)
        """
        model = "gpt-4" if use_gpt4 else "gpt-3.5-turbo"

        # Avval bozor tahlilini yaratish
        market_data = await self._generate_market_analysis(
            project_info=answers[1] if len(answers) > 1 else "",
            target_audience=answers[5] if len(answers) > 5 else "",
            model=model
        )

        # To'liq pitch content yaratish
        prompt = self._build_pitch_deck_prompt(answers, market_data)

        try:
            logger.info(f"OpenAI: Pitch deck content yaratish boshlandi (model: {model})")

            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Siz O'zbekistondagi eng tajribali pitch deck mutaxassisisiz. Juda batafsil, to'liq va professional content yarating."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.8,
                response_format={"type": "json_object"}
            )

            content = json.loads(response.choices[0].message.content)
            logger.info(f"OpenAI: Pitch deck content yaratildi")

            return content

        except Exception as e:
            logger.error(f"OpenAI xato: {e}")
            return self._generate_fallback_pitch_content(answers)

    async def generate_presentation_content(
            self,
            topic: str,
            details: str,
            slide_count: int,
            use_gpt4: bool = False,
            language: str = "uz"
    ) -> Dict:
        """
        Professional prezentatsiya uchun content yaratish
        GPT-4o bilan ishlaydi
        """
        model = "gpt-4o-mini"

        lang_map = {
            "uz": "O'zbek tilida",
            "ru": "На русском языке",
            "en": "In English"
        }
        lang_instruction = lang_map.get(language, "O'zbek tilida")

        # Til bo'yicha system prompt
        system_prompts = {
            "uz": "Siz professional prezentatsiya mutaxassisisiz. BATAFSIL, MAZMUNLI va INFORMATIV kontent yarating. Har bir slayd to'liq ma'lumotga ega bo'lsin — kam matn yozish MUMKIN EMAS. O'zbek tilida professional uslubda yozing. image_keywords INGLIZ tilida. Har bir bullet_point 1-2 jumla bo'lsin, oddiy ro'yxat emas.",
            "ru": "Вы профессиональный эксперт по презентациям. Создайте ПОДРОБНЫЙ, СОДЕРЖАТЕЛЬНЫЙ и ИНФОРМАТИВНЫЙ контент. Каждый слайд должен быть полноценным — писать мало текста НЕЛЬЗЯ. Пишите на русском языке профессиональным стилем. image_keywords на АНГЛИЙСКОМ языке. Каждый bullet_point — 1-2 предложения, не просто список.",
            "en": "You are a professional presentation expert. Create DETAILED, MEANINGFUL and INFORMATIVE content. Each slide must have full content — writing too little is NOT allowed. Write in English in a professional style. image_keywords in ENGLISH. Each bullet_point should be 1-2 sentences, not just a simple list."
        }
        system_prompt = system_prompts.get(language, system_prompts["uz"])

        # Til bo'yicha prompt qoidalari
        rules_map = {
            "uz": """KONTENT QOIDALARI:
1. Har bir slayd sarlavhasi aniq va tushunarli bo'lsin (4-8 so'z)
2. Har bir slayd uchun "content" maydoni — 3-5 ta to'liq jumla yozing. Batafsil, informativ matn.
3. Har bir slaydda 5-7 ta bullet_points bo'lsin. Har bir bullet — 1-2 jumla, batafsil va foydali ma'lumot.
4. Slaydlar orasida mantiqiy bog'lanish bo'lsin.
5. Kirish slaydida mavzuning dolzarbligi va maqsadi yozilsin.
6. Xulosa slaydida asosiy xulosalar va takliflar bo'lsin.
7. O'rtadagi slaydlarda mavzuning turli jihatlarini batafsil yoritib bering.""",
            "ru": """ПРАВИЛА КОНТЕНТА:
1. Заголовок каждого слайда — чёткий и понятный (4-8 слов)
2. Поле "content" — 3-5 полных предложений. Подробный, информативный текст.
3. В каждом слайде 5-7 bullet_points. Каждый — 1-2 предложения с полезной информацией.
4. Между слайдами должна быть логическая связь.
5. Вводный слайд — актуальность темы и цель.
6. Заключительный слайд — основные выводы и рекомендации.
7. В остальных слайдах раскройте разные аспекты темы.""",
            "en": """CONTENT RULES:
1. Each slide title should be clear and concise (4-8 words)
2. "content" field — 3-5 full sentences. Detailed, informative text.
3. Each slide should have 5-7 bullet_points. Each bullet — 1-2 sentences with useful information.
4. Slides should have logical flow between them.
5. Introduction slide — relevance of the topic and purpose.
6. Conclusion slide — key takeaways and recommendations.
7. Middle slides should cover different aspects of the topic in detail."""
        }
        rules = rules_map.get(language, rules_map["uz"])

        prompt = f"""You are an expert presentation creator. Create professional, detailed presentation content.

TOPIC: {topic}
ADDITIONAL INFO: {details or "None"}
NUMBER OF SLIDES: {slide_count}

CRITICAL LANGUAGE REQUIREMENT: ALL text content (title, subtitle, content, bullet_points) MUST be written {lang_instruction}. This is mandatory — do NOT use any other language for the content.

{rules}

IMAGE KEYWORDS (ALWAYS IN ENGLISH):
- 3 keywords per slide: primary, secondary, fallback
- primary: CONCRETE, PHOTOGRAPHABLE thing (2-3 words). Example: "students classroom desks", "doctor examining patient"
- secondary: Broader concept (2 words). Example: "education learning"
- fallback: Single simple word: "school", "hospital", "energy"
- DO NOT use abstract words: "innovation", "synergy", "strategy", "paradigm"

Return JSON:
{{
  "title": "Presentation title (impactful, 5-10 words) — {lang_instruction}",
  "subtitle": "Short description (1-2 sentences) — {lang_instruction}",
  "slides": [
    {{
      "slide_number": 1,
      "title": "Slide title (4-8 words) — {lang_instruction}",
      "content": "3-5 full sentences — {lang_instruction}",
      "bullet_points": [
        "First point — 1-2 sentences — {lang_instruction}",
        "Second point — specific data or fact",
        "Third point — practical example",
        "Fourth point — additional info",
        "Fifth point — important aspect"
      ],
      "image_keywords": {{
        "primary": "concrete photographable scene IN ENGLISH",
        "secondary": "broader visual concept IN ENGLISH",
        "fallback": "simple word IN ENGLISH"
      }}
    }}
  ]
}}

Create {slide_count} slides. First — introduction, last — conclusion. EVERY SLIDE MUST BE DETAILED!
REMEMBER: All text MUST be {lang_instruction}. Only image_keywords in English."""

        try:
            logger.info(f"OpenAI: Prezentatsiya content yaratish (model: {model}, lang: {language})")

            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=8000,
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            content = json.loads(response.choices[0].message.content)
            logger.info(f"OpenAI: Prezentatsiya content yaratildi")

            return content

        except Exception as e:
            logger.error(f"OpenAI xato: {e}")
            return self._generate_fallback_presentation_content(topic, details, slide_count)

    async def _generate_market_analysis(self, project_info: str, target_audience: str, model: str) -> Dict:
        """Bozor tahlili yaratish"""

        prompt = f"""
Loyiha: {project_info}
Auditoriya: {target_audience}

Bozor tahlili JSON:
{{
  "tam": "100 mln dollar",
  "sam": "30 mln dollar",
  "som": "5 mln dollar",
  "growth_rate": "25% yillik",
  "trends": "• Trend 1\\n• Trend 2",
  "segments": "• Segment 1\\n• Segment 2"
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Siz bozor tahlili mutaxassisisiz."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            return json.loads(response.choices[0].message.content)

        except:
            return {
                'tam': "100 mln dollar",
                'sam': "30 mln dollar",
                'som': "5 mln dollar",
                'growth_rate': "25% yillik",
                'trends': "• Raqamlashtirish\n• Mobil yechimlar",
                'segments': "• B2B: 60%\n• B2C: 40%"
            }

    def _build_pitch_deck_prompt(self, answers: List[str], market_data: Dict) -> str:
        """Pitch deck prompt"""

        return f"""
O'zbekistondagi eng yaxshi pitch deck mutaxassisisiz. BATAFSIL content yarating.

STARTUP:
Asoschi: {answers[0] if len(answers) > 0 else ""}
Loyiha: {answers[1] if len(answers) > 1 else ""}
Tavsif: {answers[2] if len(answers) > 2 else ""}
Muammo: {answers[3] if len(answers) > 3 else ""}
Yechim: {answers[4] if len(answers) > 4 else ""}
Auditoriya: {answers[5] if len(answers) > 5 else ""}
Biznes: {answers[6] if len(answers) > 6 else ""}
Raqobat: {answers[7] if len(answers) > 7 else ""}
Ustunlik: {answers[8] if len(answers) > 8 else ""}
Moliya: {answers[9] if len(answers) > 9 else ""}

BOZOR: {json.dumps(market_data, ensure_ascii=False)}

JSON qaytaring:
{{
  "project_name": "Loyiha nomi",
  "author": "Ism",
  "tagline": "Shior (8-10 so'z)",
  "problem_title": "MUAMMO",
  "problem": "Batafsil muammo (5-7 jumla)",
  "solution_title": "YECHIM",
  "solution": "Batafsil yechim (5-7 jumla)",
  "market_title": "BOZOR",
  "market": "Bozor tahlili",
  "business_title": "BIZNES",
  "business_model": "Daromad modeli",
  "competition_title": "RAQOBAT",
  "competition": "Raqobatchilar tahlili",
  "advantage_title": "USTUNLIK",
  "advantage": "Ustunliklar",
  "financials_title": "MOLIYA",
  "financials": "Moliyaviy prognoz",
  "team_title": "JAMOA",
  "team": "Jamoa a'zolari",
  "milestones_title": "YO'L XARITASI",
  "milestones": "Bosqichlar",
  "cta": "Chaqiruv"
}}
"""

    def _generate_fallback_pitch_content(self, answers: List[str]) -> Dict:
        """Fallback pitch content"""
        return {
            'project_name': answers[1] if len(answers) > 1 else "Innovatsion Loyiha",
            'author': answers[0] if len(answers) > 0 else "Tadbirkor",
            'tagline': "Kelajakni birgalikda quramiz",
            'problem_title': "MUAMMO",
            'problem': f"• Asosiy muammo: {answers[3] if len(answers) > 3 else 'Bozordagi samarasizlik'}\nKo'plab kompaniyalar kurashmoqda.",
            'solution_title': "YECHIM",
            'solution': f"• Yechim: {answers[4] if len(answers) > 4 else 'Innovatsion platforma'}\nZamonaviy texnologiyalar orqali hal qilamiz.",
            'market_title': "BOZOR",
            'market': f"📊 BOZOR:\n• TAM: 500 mln dollar\n• SAM: 150 mln dollar\n• SOM: 30 mln dollar\n\n🎯 Auditoriya: {answers[5] if len(answers) > 5 else 'B2B va B2C'}",
            'business_title': "BIZNES",
            'business_model': f"💰 {answers[6] if len(answers) > 6 else 'SaaS subscription'}\n• Oylik: 50,000-500,000 so'm",
            'competition_title': "RAQOBAT",
            'competition': f"🏆 {answers[7] if len(answers) > 7 else 'Mahalliy va xalqaro'}\nUstunlik: Mahalliy bozorni tushunish",
            'advantage_title': "USTUNLIK",
            'advantage': f"⭐ {answers[8] if len(answers) > 8 else 'Yagona mahalliy yechim'}\n1. TEXNOLOGIK\n2. NARX\n3. MAHALLIY",
            'financials_title': "MOLIYA",
            'financials': f"📊 {answers[9] if len(answers) > 9 else 'Ijobiy'}\n• 1-yil: 500 mln so'm",
            'team_title': "JAMOA",
            'team': "👥 PROFESSIONAL JAMOA\n• CEO: 10+ yil\n• CTO: 8+ yil",
            'milestones_title': "YO'L XARITASI",
            'milestones': "🗓️ BOSQICHLAR:\n• 0-3 OY: MVP\n• 3-6 OY: 500 mijoz\n• 6-12 OY: Break-even",
            'cta': "Keling, birgalikda yangi standartlar o'rnatamiz! 🚀"
        }

    def _generate_fallback_presentation_content(self, topic: str, details: str, slide_count: int) -> Dict:
        """Fallback prezentatsiya content"""
        slides = []

        # Mavzudan kalit so'z yaratish
        topic_words = topic.lower().split()
        base_keyword = topic_words[0] if topic_words else "presentation"

        slides.append({
            "slide_number": 1,
            "title": topic,
            "content": f"{topic} haqida professional prezentatsiya.",
            "bullet_points": [],
            "image_keywords": {
                "primary": f"{base_keyword} presentation cover",
                "secondary": f"{base_keyword} concept",
                "fallback": "presentation"
            }
        })

        for i in range(2, slide_count + 1):
            slides.append({
                "slide_number": i,
                "title": f"{topic} - Bo'lim {i - 1}",
                "content": f"{topic} ning {i - 1}-qismi.",
                "bullet_points": [
                    f"{topic} asosiy jihati",
                    f"Amaliy qo'llanilishi",
                    f"Kelajak istiqbollari"
                ],
                "image_keywords": {
                    "primary": f"{base_keyword} analysis chart",
                    "secondary": f"{base_keyword} data",
                    "fallback": "business"
                }
            })

        return {
            "title": topic,
            "subtitle": details[:100] if details else f"{topic} haqida",
            "slides": slides
        }
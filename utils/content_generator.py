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
            use_gpt4: bool = False
    ) -> Dict:
        """
        Professional prezentatsiya uchun content yaratish
        GPT-4o bilan ishlaydi
        """
        model = "gpt-4o"

        prompt = f"""Siz tajribali prezentatsiya mutaxassisisiz. Professional, batafsil va mazmunli prezentatsiya kontent yarating.

MAVZU: {topic}
QO'SHIMCHA MA'LUMOT: {details or "Yo'q"}
SLAYDLAR SONI: {slide_count}

KONTENT QOIDALARI:
1. Har bir slayd sarlavhasi aniq va tushunarli bo'lsin (4-8 so'z)
2. Har bir slayd uchun "content" maydoni — 3-5 ta to'liq jumla yozing. Bu slaydning asosiy matni. Har bir jumla ma'noli va informativ bo'lsin. Mavzuni chuqur yoritib bering.
3. Har bir slaydda 5-7 ta bullet_points bo'lsin. Har bir bullet — 1-2 jumla, batafsil va foydali ma'lumot. Oddiy ro'yxat emas, balki har biri mustaqil fikr bo'lsin.
4. Slaydlar orasida mantiqiy bog'lanish bo'lsin — bir slayd ikkinchisiga olib borsin.
5. Kirish slaydida mavzuning dolzarbligi va maqsadi yozilsin.
6. Xulosa slaydida asosiy xulosalar va takliflar bo'lsin.
7. O'rtadagi slaydlarda mavzuning turli jihatlarini batafsil yoritib bering.

RASM KALIT SO'ZLARI (INGLIZ TILIDA):
- Har bir slaydga 3 ta kalit so'z: primary, secondary, fallback
- primary: ANIQ, FOTOGRAFIYA QILINADIGAN narsa (2-3 so'z). Masalan: "students classroom desks", "doctor examining patient", "solar panels rooftop"
- secondary: Kengroq tushuncha (2 so'z). Masalan: "education learning", "medical clinic"
- fallback: Bitta oddiy so'z: "school", "hospital", "energy"
- ABSTRAKT so'zlar ISHLATMANG: "innovation", "synergy", "strategy", "paradigm"
- Test: "Fotograf buni suratga ola oladimi?" Agar yo'q — almashtiring

JSON formatida qaytaring:
{{
  "title": "Prezentatsiya sarlavhasi (ta'sirli, 5-10 so'z)",
  "subtitle": "Mavzuning qisqa tavsifi (1-2 jumla)",
  "slides": [
    {{
      "slide_number": 1,
      "title": "Slayd sarlavhasi (4-8 so'z)",
      "content": "3-5 ta to'liq jumla. Batafsil, informativ matn. Mavzuni chuqur yoritib bering.",
      "bullet_points": [
        "Birinchi nuqta — 1-2 jumla bilan batafsil tushuntiring",
        "Ikkinchi nuqta — aniq ma'lumot yoki fakt keltiring",
        "Uchinchi nuqta — amaliy misol yoki dalil",
        "To'rtinchi nuqta — qo'shimcha ma'lumot",
        "Beshinchi nuqta — muhim jihat"
      ],
      "image_keywords": {{
        "primary": "aniq fotografiya qilinadigan sahna",
        "secondary": "kengroq vizual tushuncha",
        "fallback": "oddiy so'z"
      }}
    }}
  ]
}}

{slide_count} ta slayd yarating. Birinchi — kirish, oxirgi — xulosa. HAR BIR SLAYD BATAFSIL BO'LSIN!"""

        try:
            logger.info(f"OpenAI: Prezentatsiya content yaratish (model: {model})")

            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Siz professional prezentatsiya mutaxassisisiz. BATAFSIL, MAZMUNLI va INFORMATIV kontent yarating. Har bir slayd to'liq ma'lumotga ega bo'lsin — kam matn yozish MUMKIN EMAS. O'zbek tilida professional uslubda yozing. image_keywords INGLIZ tilida. Har bir bullet_point 1-2 jumla bo'lsin, oddiy ro'yxat emas."
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
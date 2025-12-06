import asyncio
import json
import logging
from typing import Dict, List, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class ContentGenerator:
    """
    OpenAI API bilan professional content yaratish
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
        Oddiy prezentatsiya uchun content yaratish

        Args:
            topic: Prezentatsiya mavzusi
            details: Qo'shimcha ma'lumotlar
            slide_count: Slaydlar soni

        Returns:
            Prezentatsiya content (JSON)
        """
        model = "gpt-4" if use_gpt4 else "gpt-3.5-turbo"

        prompt = f"""
Siz professional prezentatsiya mutaxassisisiz. O'zbek tilida prezentatsiya content yarating.

MAVZU: {topic}

QO'SHIMCHA: {details}

SLAYDLAR: {slide_count}

JSON formatida qaytaring:
{{
  "title": "Prezentatsiya sarlavhasi",
  "subtitle": "Qisqa tavsif",
  "slides": [
    {{
      "slide_number": 1,
      "title": "Slayd sarlavhasi",
      "content": "Slayd mazmuni (3-5 jumla)",
      "bullet_points": [
        "Birinchi nuqta (2-3 jumla)",
        "Ikkinchi nuqta (2-3 jumla)",
        "Uchinchi nuqta (2-3 jumla)"
      ]
    }}
  ]
}}

Jami {slide_count} ta slayd yarating. HAR BIR SLAYD BATAFSIL!
"""

        try:
            logger.info(f"OpenAI: Prezentatsiya content yaratish boshlandi (model: {model})")

            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Siz professional prezentatsiya yaratuvchisiz. O'zbek tilida javob bering."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=3000,
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

        slides.append({
            "slide_number": 1,
            "title": topic,
            "content": f"{topic} haqida professional prezentatsiya. {details[:100]}",
            "bullet_points": []
        })

        for i in range(2, slide_count + 1):
            slides.append({
                "slide_number": i,
                "title": f"{topic} - Bo'lim {i - 1}",
                "content": f"{topic} ning {i - 1}-qismi. {details[:50]}",
                "bullet_points": [
                    f"Birinchi nuqta: {topic} asosiy jihati",
                    f"Ikkinchi nuqta: Amaliy qo'llanilishi",
                    f"Uchinchi nuqta: Kelajak istiqbollari"
                ]
            })

        return {
            "title": topic,
            "subtitle": details[:100] if details else f"{topic} haqida",
            "slides": slides
        }
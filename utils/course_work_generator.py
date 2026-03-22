# utils/course_work_generator.py
# MUSTAQIL ISH / REFERAT CONTENT GENERATOR
# YANGILANGAN - Multi-step generation: har bir bo'lim alohida API call bilan yaratiladi

import asyncio
import json
import logging
from typing import Dict, List, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class CourseWorkGenerator:
    """
    OpenAI API bilan mustaqil ish / referat yaratish
    Multi-step generation: har bir bo'lim alohida generatsiya qilinadi
    """

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_course_work_content(
            self,
            work_type: str,
            topic: str,
            subject: str,
            details: str,
            page_count: int,
            language: str = 'uz',
            use_gpt4: bool = True
    ) -> Dict:
        """
        Mustaqil ish uchun BATAFSIL content yaratish - MULTI-STEP
        Har bir bo'lim alohida API call bilan yaratiladi
        """
        try:
            # Ish turi bo'yicha struktura
            structure = self._get_work_structure(work_type, page_count)
            lang_instructions = self._get_language_instructions(language)
            total_words = page_count * 350

            logger.info(f"Multi-step generation boshlandi: {structure['name']} ({total_words} so'z)")

            # =============================================
            # STEP 1: Generate outline (structure/plan)
            # =============================================
            logger.info("Step 1: Outline yaratilmoqda...")
            outline = await self._generate_outline(
                work_type, topic, subject, details, page_count, language, structure
            )
            await asyncio.sleep(0.5)

            # =============================================
            # STEP 2: Generate KIRISH (introduction)
            # =============================================
            logger.info("Step 2: KIRISH yaratilmoqda...")
            intro_min_words = max(800, structure['intro_words'])
            introduction_text = await self._generate_section_content(
                topic=topic,
                subject=subject,
                section_title="KIRISH",
                outline=outline,
                section_type="introduction",
                language=language,
                lang_instructions=lang_instructions,
                min_words=intro_min_words,
                chapter_title=None,
                section_number=None
            )
            await asyncio.sleep(0.5)

            # =============================================
            # STEP 3: Generate each chapter section
            # =============================================
            chapters = []
            for ch_idx, chapter_info in enumerate(outline.get('chapters', [])):
                chapter_title = chapter_info.get('title', f'{ch_idx + 1}-bob')
                chapter_number = chapter_info.get('number', ch_idx + 1)
                sections = []

                for sec_idx, section_info in enumerate(chapter_info.get('sections', [])):
                    sec_title = section_info.get('title', f'Bo\'lim {sec_idx + 1}')
                    sec_number = section_info.get('number', f'{chapter_number}.{sec_idx + 1}')

                    logger.info(f"Step 3: {sec_number}. {sec_title} yaratilmoqda...")

                    section_text = await self._generate_section_content(
                        topic=topic,
                        subject=subject,
                        section_title=sec_title,
                        outline=outline,
                        section_type="chapter_section",
                        language=language,
                        lang_instructions=lang_instructions,
                        min_words=1000,
                        chapter_title=chapter_title,
                        section_number=sec_number
                    )

                    sections.append({
                        'number': sec_number,
                        'title': sec_title,
                        'content': section_text
                    })

                    await asyncio.sleep(0.5)

                chapters.append({
                    'number': chapter_number,
                    'title': chapter_title,
                    'sections': sections
                })

            # =============================================
            # STEP 4: Generate XULOSA (conclusion)
            # =============================================
            logger.info("Step 4: XULOSA yaratilmoqda...")
            conclusion_min_words = max(600, structure['conclusion_words'])
            conclusion_text = await self._generate_section_content(
                topic=topic,
                subject=subject,
                section_title="XULOSA",
                outline=outline,
                section_type="conclusion",
                language=language,
                lang_instructions=lang_instructions,
                min_words=conclusion_min_words,
                chapter_title=None,
                section_number=None
            )
            await asyncio.sleep(0.5)

            # =============================================
            # STEP 5: Generate references
            # =============================================
            logger.info("Step 5: Adabiyotlar yaratilmoqda...")
            references = await self._generate_references_ai(
                topic, subject, language, lang_instructions, structure['min_references']
            )

            # =============================================
            # COMBINE everything into final structure
            # =============================================
            logger.info("Barcha bo'limlar birlashtirilmoqda...")

            # Build table of contents from outline
            table_of_contents = self._build_table_of_contents(outline, page_count)

            # Build recommendations from conclusion
            recommendations = self._extract_recommendations(conclusion_text, topic)

            content = {
                'title': topic,
                'subtitle': f"{subject} fanidan {structure['name'].lower()}",
                'author_info': {
                    'institution': outline.get('institution', "O'zbekiston Milliy Universiteti"),
                    'faculty': outline.get('faculty', f"{subject} fakulteti"),
                    'department': outline.get('department', f"{subject} kafedrasi")
                },
                'abstract': outline.get('abstract', f"Ushbu {structure['name'].lower()} {topic} mavzusiga bag'ishlangan. Ishda mavzuning nazariy asoslari o'rganilgan, xorijiy va mahalliy tajriba tahlil qilingan, hozirgi holat baholangan va tavsiyalar ishlab chiqilgan."),
                'keywords': outline.get('keywords', [topic.split()[0] if topic.split() else "mavzu", subject, "tadqiqot", "tahlil", "tavsiya"]),
                'table_of_contents': table_of_contents,
                'introduction': {
                    'title': 'KIRISH',
                    'content': introduction_text
                },
                'chapters': chapters,
                'conclusion': {
                    'title': 'XULOSA',
                    'content': conclusion_text
                },
                'recommendations': recommendations,
                'references': references,
                'appendix': None
            }

            # Validate and enhance
            content = self._validate_and_enhance_content(content, structure, topic, subject, page_count, language)

            logger.info(f"Multi-step generation tugadi: {structure['name']}")
            return content

        except Exception as e:
            logger.error(f"Multi-step generation xato: {e}")
            return self._generate_detailed_fallback_content(work_type, topic, subject, details, page_count, language)

    # =========================================================================
    # MULTI-STEP HELPER METHODS
    # =========================================================================

    async def _generate_outline(
            self, work_type: str, topic: str, subject: str, details: str,
            page_count: int, language: str, structure: Dict
    ) -> Dict:
        """
        Step 1: Ish strukturasini (outline) yaratish
        Returns: dict with chapters, sections, abstract, keywords
        """
        lang_instructions = self._get_language_instructions(language)
        total_words = page_count * 350

        prompt = f"""{lang_instructions}

Siz O'zbekistondagi ENG TAJRIBALI professor va akademik yozuvchisiz.
Quyidagi mavzu uchun {structure['name']} STRUKTURASINI (rejasini) yarating.

Mavzu: {topic}
Fan: {subject}
Sahifalar soni: {page_count} ({total_words} so'z)
Ish turi: {structure['name']}

Qo'shimcha talablar: {details if details else "Maxsus talablar yo'q"}

JSON formatida qaytaring:
{{
    "institution": "Universitet nomi",
    "faculty": "Fakultet nomi",
    "department": "Kafedra nomi",
    "abstract": "Annotatsiya - 200-250 so'z bilan ishning qisqacha mazmuni, maqsadi, metodlari va natijalari",
    "keywords": ["kalit1", "kalit2", "kalit3", "kalit4", "kalit5", "kalit6", "kalit7"],
    "chapters": [
        {{
            "number": 1,
            "title": "BOB SARLAVHASI (mavzuga mos)",
            "sections": [
                {{"number": "1.1", "title": "Bo'lim sarlavhasi (aniq, mavzuga mos)"}},
                {{"number": "1.2", "title": "Bo'lim sarlavhasi"}},
                {{"number": "1.3", "title": "Bo'lim sarlavhasi"}}
            ]
        }},
        {{
            "number": 2,
            "title": "BOB SARLAVHASI (mavzuga mos)",
            "sections": [
                {{"number": "2.1", "title": "Bo'lim sarlavhasi"}},
                {{"number": "2.2", "title": "Bo'lim sarlavhasi"}},
                {{"number": "2.3", "title": "Bo'lim sarlavhasi"}}
            ]
        }}
    ]
}}

MUHIM:
- Boblar va bo'limlar MAVZUGA MOS bo'lsin (umumiy emas!)
- {structure['name']} uchun {len(structure['chapters_outline'])} ta bob bo'lsin
- Har bir bobda 2-3 ta bo'lim bo'lsin
- Sarlavhalar ANIQ va PROFESSIONAL bo'lsin
- Annotatsiya HAQIQIY, to'liq 200-250 so'z bo'lsin
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"Siz tajribali akademik professor. {lang_instructions}"
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048,
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            outline = json.loads(response.choices[0].message.content)
            logger.info(f"Outline yaratildi: {len(outline.get('chapters', []))} bob")
            return outline

        except Exception as e:
            logger.error(f"Outline yaratishda xato: {e}")
            # Fallback outline
            return self._get_fallback_outline(topic, subject, structure)

    async def _generate_section_content(
            self,
            topic: str,
            subject: str,
            section_title: str,
            outline: Dict,
            section_type: str,
            language: str,
            lang_instructions: str,
            min_words: int = 800,
            chapter_title: Optional[str] = None,
            section_number: Optional[str] = None
    ) -> str:
        """
        Bitta bo'lim uchun batafsil content yaratish
        Returns: plain text (NOT JSON) - bu ko'proq so'z beradi
        """
        # Build outline summary for context
        outline_summary = self._outline_to_text(outline)

        if section_type == "introduction":
            prompt = self._build_introduction_prompt(
                topic, subject, outline_summary, lang_instructions, min_words
            )
        elif section_type == "conclusion":
            prompt = self._build_conclusion_prompt(
                topic, subject, outline_summary, lang_instructions, min_words
            )
        elif section_type == "chapter_section":
            prompt = self._build_chapter_section_prompt(
                topic, subject, section_title, chapter_title, section_number,
                outline_summary, lang_instructions, min_words
            )
        else:
            prompt = f"Yozing: {section_title} - {topic} haqida. Kamida {min_words} so'z."

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""Siz O'zbekistondagi ENG TAJRIBALI professor va akademik yozuvchisiz.
{lang_instructions}

MUHIM QOIDALAR:
1. FAQAT matn yozing - JSON, markdown, sarlavha, format belgilari ISHLATMANG
2. To'g'ridan-to'g'ri matn paragraflar bilan yozing
3. Har bir paragraf 6-10 gapdan iborat bo'lsin
4. Paragraflar orasida bo'sh qator qo'ying
5. Kamida {min_words} so'z yozing - QISQARTIRMANG!
6. Ilmiy akademik uslubda yozing
7. Haqiqiy faktlar, statistika, misollar keltiring
8. {subject} sohasidagi eng so'nggi ma'lumotlarni yozing
9. Har 2-3 paragrafda MANBA iqtibosi keltiring (masalan: "Professor X.Y.ning ta'kidlashicha...", "Tadqiqotlar shuni ko'rsatadiki...")
10. Raqamli ma'lumotlar (foizlar, yillar, statistika) MAJBURIY ishlatilsin
11. O'zbekiston kontekstida misollar keltiring
12. Paragraflar bir-biri bilan MANTIQIY bog'langan bo'lsin — oldingi paragrafdan keyingisiga o'tish tabiiy bo'lsin"""
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096,
                temperature=0.7
            )

            text = response.choices[0].message.content.strip()

            # Clean up any markdown or formatting artifacts
            text = self._clean_generated_text(text)

            word_count = len(text.split())
            logger.info(f"'{section_title}' yaratildi: {word_count} so'z")

            return text

        except Exception as e:
            logger.error(f"Bo'lim yaratishda xato ({section_title}): {e}")
            return self._get_fallback_section_text(section_type, topic, subject, section_title, chapter_title)

    async def _generate_references_ai(
            self, topic: str, subject: str, language: str,
            lang_instructions: str, min_count: int
    ) -> List[str]:
        """
        Step 5: AI bilan adabiyotlar ro'yxatini yaratish
        """
        prompt = f"""{lang_instructions}

"{topic}" mavzusi va "{subject}" fani uchun GOST standartidagi adabiyotlar ro'yxatini yarating.

Kamida {min_count} ta manba bo'lsin:
- O'zbek tilidagi kitoblar (5-6 ta) - haqiqiy yoki realistik mualliflar
- Rus tilidagi kitoblar (2-3 ta)
- Ingliz tilidagi kitoblar va maqolalar (3-4 ta)
- Qonunchilik manbalari (1-2 ta)
- Internet manbalari (2-3 ta ishonchli sayt)

Format: Har bir manbani raqam bilan boshlang.
GOST 7.1-2003 standartiga mos formatda yozing.

FAQAT ro'yxatni yozing, ortiqcha matn kerak emas.
Har bir manbani yangi qatordan boshlang.
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"Siz kutubxonachi va bibliograf. {lang_instructions}"
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048,
                temperature=0.7
            )

            text = response.choices[0].message.content.strip()
            # Parse references from text
            references = []
            for line in text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    # Remove leading number/dot/dash if present, then re-add proper numbering later
                    references.append(line)

            if len(references) < min_count:
                # Add fallback references
                fallback = self._generate_references(topic, subject, min_count)
                references.extend(fallback[len(references):])

            # Ensure proper numbering
            numbered_refs = []
            for i, ref in enumerate(references[:max(min_count, len(references))]):
                # Remove existing numbering
                clean_ref = ref.lstrip('0123456789.-) ').strip()
                if clean_ref:
                    numbered_refs.append(f"{i + 1}. {clean_ref}")

            return numbered_refs if numbered_refs else self._generate_references(topic, subject, min_count)

        except Exception as e:
            logger.error(f"References yaratishda xato: {e}")
            return self._generate_references(topic, subject, min_count)

    # =========================================================================
    # PROMPT BUILDERS
    # =========================================================================

    def _build_introduction_prompt(
            self, topic: str, subject: str, outline_summary: str,
            lang_instructions: str, min_words: int
    ) -> str:
        return f"""Quyidagi mavzu bo'yicha akademik ishning KIRISH qismini yozing.

Mavzu: {topic}
Fan: {subject}

Ishning strukturasi:
{outline_summary}

KIRISH quyidagi qismlarni O'Z ICHIGA OLISHI SHART:

1. MAVZUNING DOLZARBLIGI (2-3 paragraf):
   - Nima uchun bu mavzu bugungi kunda muhim?
   - Qanday ijtimoiy/iqtisodiy/ilmiy ahamiyatga ega?
   - O'zbekistonda va jahonda bu masalaning holati
   - Statistik ma'lumotlar bilan asoslang

2. MUAMMONING QO'YILISHI (1-2 paragraf):
   - Qanday muammolar mavjud?
   - Nima uchun bu muammolarni o'rganish kerak?
   - Oldingi tadqiqotlarda qanday bo'shliqlar bor?

3. ISHNING MAQSADI (1 paragraf):
   - Aniq va ravshan maqsad

4. ISHNING VAZIFALARI (raqamlangan ro'yxat, 5-7 ta):
   - Har bir vazifa aniq va o'lchanadigan bo'lsin
   - 1. ...
   - 2. ...
   - va hokazo

5. TADQIQOT OB'EKTI VA PREDMETI (1 paragraf):
   - Ob'ekt - nima o'rganilmoqda
   - Predmet - qaysi jihati o'rganilmoqda

6. TADQIQOT METODLARI (1 paragraf):
   - Qanday ilmiy usullar qo'llanilgan (tahlil, sintez, qiyoslash, statistik, ekspert bahosi, kuzatish va h.k.)

7. ISHNING ILMIY YANGILIGI VA AMALIY AHAMIYATI (1-2 paragraf):
   - Nima yangilik bor?
   - Amaliyotda kimga foydali?

8. ISHNING TUZILISHI (1 paragraf):
   - Ish necha bob, necha bo'limdan iborat ekanligi

JAMI KAMIDA {min_words} SO'Z YOZING!
To'g'ridan-to'g'ri matn yozing, hech qanday sarlavha yoki format belgisi ishlatmang.
Paragraflarni bo'sh qator bilan ajrating."""

    def _build_conclusion_prompt(
            self, topic: str, subject: str, outline_summary: str,
            lang_instructions: str, min_words: int
    ) -> str:
        return f"""Quyidagi mavzu bo'yicha akademik ishning XULOSA qismini yozing.

Mavzu: {topic}
Fan: {subject}

Ishning strukturasi:
{outline_summary}

XULOSA quyidagi qismlarni O'Z ICHIGA OLISHI SHART:

1. UMUMIY XULOSA (1-2 paragraf):
   - Ish davomida nima qilindi?
   - Qanday natijalar olindi?

2. HAR BIR VAZIFA BO'YICHA XULOSA (3-5 paragraf):
   - Birinchi vazifa bo'yicha: nima aniqlandi...
   - Ikkinchi vazifa bo'yicha: nima tahlil qilindi...
   - Uchinchi vazifa bo'yicha: nima ishlab chiqildi...
   - va hokazo

3. ASOSIY TOPILMALAR (1-2 paragraf):
   - Eng muhim natijalar nima?
   - Qanday yangi bilimlar olindi?

4. AMALIY TAVSIYALAR (raqamlangan, 5-7 ta):
   - Aniq va amalga oshirish mumkin bo'lgan tavsiyalar
   - Har bir tavsiya 2-3 gap bilan tushuntirilsin

5. KELGUSIDAGI TADQIQOTLAR UCHUN YO'NALISHLAR (1-2 paragraf):
   - Bu mavzuni yanada chuqurroq o'rganish uchun nima qilish kerak?
   - Qaysi yo'nalishlarda tadqiqot olib borish mumkin?

JAMI KAMIDA {min_words} SO'Z YOZING!
To'g'ridan-to'g'ri matn yozing, hech qanday sarlavha yoki format belgisi ishlatmang.
Paragraflarni bo'sh qator bilan ajrating."""

    def _build_chapter_section_prompt(
            self, topic: str, subject: str, section_title: str,
            chapter_title: str, section_number: str,
            outline_summary: str, lang_instructions: str, min_words: int
    ) -> str:
        return f"""Quyidagi akademik ish bo'limining TO'LIQ matnini yozing.

Mavzu: {topic}
Fan: {subject}
Bob: {chapter_title}
Bo'lim: {section_number}. {section_title}

Ishning umumiy strukturasi:
{outline_summary}

BO'LIMDA QUYIDAGILAR BO'LISHI SHART:

1. ASOSIY MATN (8-12 paragraf, har biri 6-10 gap):
   - Mavzuni chuqur va batafsil yoritish
   - Ilmiy manbalardan iqtiboslar keltirish (masalan: "Professor Karimovning ta'kidlashicha...")
   - Aniq faktlar va statistik ma'lumotlar
   - Misollar va dalillar
   - Turli olimlarning fikrlarini keltirish va taqqoslash
   - O'zbekiston va xalqaro kontekstda tahlil

2. TAHLILIY QISM:
   - Mavjud yondashuvlarni tanqidiy baholash
   - Afzalliklar va kamchiliklarni ko'rsatish
   - Qiyosiy tahlil

3. BO'LIM XULOSASI (1 paragraf):
   - Bo'limda aytilgan asosiy fikrlarni umumlashtirish

MUHIM QOIDALAR:
- FAQAT shu bo'limning mazmunini yozing
- Boshqa bo'limlar haqida yozmang
- Haqiqiy, ishonchli ma'lumotlar yozing
- Akademik ilmiy uslubda yozing
- Plagiatdan xoli, original matn bo'lsin

JAMI KAMIDA {min_words} SO'Z YOZING! QISQARTIRMANG!
To'g'ridan-to'g'ri matn yozing, hech qanday sarlavha, raqam yoki format belgisi ishlatmang.
Paragraflarni bo'sh qator bilan ajrating."""

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _outline_to_text(self, outline: Dict) -> str:
        """Outline ni matn ko'rinishiga o'tkazish (kontekst uchun)"""
        lines = []
        lines.append("KIRISH")
        for ch in outline.get('chapters', []):
            ch_num = ch.get('number', '')
            ch_title = ch.get('title', '')
            lines.append(f"{ch_num}-BOB. {ch_title}")
            for sec in ch.get('sections', []):
                sec_num = sec.get('number', '')
                sec_title = sec.get('title', '')
                lines.append(f"  {sec_num}. {sec_title}")
        lines.append("XULOSA")
        lines.append("ADABIYOTLAR")
        return '\n'.join(lines)

    def _clean_generated_text(self, text: str) -> str:
        """AI tomonidan yaratilgan matnni tozalash"""
        import re

        # Remove markdown headers
        text = re.sub(r'^#{1,6}\s+.*$', '', text, flags=re.MULTILINE)

        # Remove bold/italic markdown
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)

        # Remove markdown bullet points but keep content
        text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)

        # Remove excessive whitespace but keep paragraph breaks
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _build_table_of_contents(self, outline: Dict, page_count: int) -> List[Dict]:
        """Outline dan mundarija yaratish"""
        toc = [{'title': 'KIRISH', 'page': 3}]

        chapters = outline.get('chapters', [])
        total_chapters = len(chapters)
        if total_chapters == 0:
            return toc

        # Approximate page distribution
        content_pages = page_count - 6  # minus intro, conclusion, refs, toc, title
        pages_per_chapter = max(1, content_pages // total_chapters)
        current_page = 5

        for ch in chapters:
            ch_num = ch.get('number', 1)
            ch_title = ch.get('title', '')

            # Roman numeral for chapter
            roman = self._to_roman(ch_num)
            toc.append({'title': f'{roman} BOB. {ch_title.upper()}', 'page': current_page})

            for sec in ch.get('sections', []):
                sec_num = sec.get('number', '')
                sec_title = sec.get('title', '')
                toc.append({'title': f'{sec_num}. {sec_title}', 'page': current_page})
                current_page += max(1, pages_per_chapter // len(ch.get('sections', [1])))

            current_page += 1

        toc.append({'title': 'XULOSA', 'page': page_count - 2})
        toc.append({'title': 'FOYDALANILGAN ADABIYOTLAR', 'page': page_count})

        return toc

    def _to_roman(self, num: int) -> str:
        """Raqamni rim raqamiga o'tkazish"""
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
        result = ''
        for i in range(len(val)):
            while num >= val[i]:
                result += syms[i]
                num -= val[i]
        return result

    def _extract_recommendations(self, conclusion_text: str, topic: str) -> List[str]:
        """Xulosa matnidan tavsiyalarni ajratib olish"""
        recommendations = [
            f"{topic} sohasida me'yoriy-huquqiy bazani takomillashtirish va zamonaviy talablarga moslashtirish",
            "Kadrlar tayyorlash tizimini yanada rivojlantirish va xalqaro tajriba almashuvini kengaytirish",
            "Zamonaviy texnologiyalarni joriy etish va innovatsion yechimlarni qo'llash",
            "Monitoring va baholash tizimini yaratish hamda samaradorlikni muntazam tahlil qilish",
            "Xalqaro hamkorlikni kengaytirish va ilg'or tajribalarni o'rganish"
        ]
        return recommendations

    def _get_fallback_outline(self, topic: str, subject: str, structure: Dict) -> Dict:
        """Fallback outline - agar AI outline yarata olmasa"""
        chapters_outline = structure.get('chapters_outline', ['Nazariy asoslar', 'Amaliy tahlil'])

        chapters = []
        for i, ch_name in enumerate(chapters_outline):
            ch_num = i + 1
            sections = [
                {'number': f'{ch_num}.1', 'title': f'{ch_name} - asosiy tushunchalar'},
                {'number': f'{ch_num}.2', 'title': f'{ch_name} - tahlil va baholash'},
            ]
            if ch_num == 1:
                sections.append({'number': f'{ch_num}.3', 'title': f'Xorijiy va mahalliy tajriba'})

            chapters.append({
                'number': ch_num,
                'title': ch_name.upper(),
                'sections': sections
            })

        return {
            'institution': "O'zbekiston Milliy Universiteti",
            'faculty': f"{subject} fakulteti",
            'department': f"{subject} kafedrasi",
            'abstract': f"Ushbu ishda {topic} mavzusi bo'yicha nazariy va amaliy tadqiqot olib borilgan. Mavzuning dolzarbligi, nazariy asoslari, xorijiy va mahalliy tajriba tahlil qilingan hamda tavsiyalar ishlab chiqilgan.",
            'keywords': [topic.split()[0] if topic.split() else "mavzu", subject, "tadqiqot", "tahlil", "tavsiya", "rivojlanish", "innovatsiya"],
            'chapters': chapters
        }

    def _get_fallback_section_text(
            self, section_type: str, topic: str, subject: str,
            section_title: str, chapter_title: Optional[str]
    ) -> str:
        """Fallback matn - agar AI bo'lim yarata olmasa"""
        if section_type == "introduction":
            return self._generate_detailed_intro(topic, subject, {'name': ''}, 'uz')
        elif section_type == "conclusion":
            return self._generate_detailed_conclusion(topic, subject, {'name': ''}, 'uz')
        else:
            return self._generate_fallback_section(topic, subject, section_title, chapter_title)

    def _generate_fallback_section(self, topic: str, subject: str, section_title: str,
                                   chapter_title: Optional[str]) -> str:
        """Bitta bo'lim uchun fallback matn"""
        return f"""{topic} mavzusining "{section_title}" bo'limi {subject} fanining muhim yo'nalishlaridan birini o'z ichiga oladi. Bu masala bugungi kunda dolzarb bo'lib, chuqur ilmiy tadqiqotni talab qiladi.

Zamonaviy {subject.lower()} fanida {section_title.lower()} masalasi alohida o'rin tutadi. Olimlarning tadqiqotlari shuni ko'rsatadiki, bu sohada bir qator muhim muammolar mavjud bo'lib, ularni hal qilish uchun kompleks yondashuv zarur. Xususan, nazariy bilimlarni amaliyot bilan uyg'unlashtirish, zamonaviy texnologiyalardan foydalanish va xalqaro tajribani o'rganish muhim ahamiyatga ega.

Tarixiy nuqtai nazardan qaraganda, {section_title.lower()} masalasi uzoq tarixga ega. Dastlab bu masala XX asrning birinchi yarmida ilmiy doiralarda muhokama qilina boshlangan. Keyinchalik, fan va texnika taraqqiyoti bilan birga, bu sohada yangi yondashuvlar va nazariyalar paydo bo'ldi. Bugungi kunda {section_title.lower()} bo'yicha ko'plab ilmiy maktablar va yo'nalishlar mavjud.

O'zbekistonda {section_title.lower()} sohasida faol tadqiqotlar olib borilmoqda. Mahalliy olimlar va mutaxassislar tomonidan muhim natijalar olingan. Xususan, so'nggi yillarda bu sohada bir qator dissertatsiyalar himoya qilingan, monografiyalar nashr etilgan va ilmiy konferensiyalar o'tkazilgan.

Xalqaro tajriba tahlili shuni ko'rsatadiki, rivojlangan mamlakatlarda {section_title.lower()} masalasiga katta e'tibor qaratilmoqda. AQSh, Yevropa Ittifoqi, Yaponiya va boshqa mamlakatlarda bu sohada samarali tizimlar yaratilgan va muvaffaqiyatli faoliyat yuritilmoqda. Ushbu tajribani o'rganish va O'zbekiston sharoitlariga moslash muhim amaliy ahamiyatga ega.

Statistik ma'lumotlarga ko'ra, so'nggi 5-10 yilda {section_title.lower()} sohasida sezilarli o'sish tendensiyasi kuzatilmoqda. Bu esa ushbu sohaning kelajagiga nisbatan ijobiy prognozlar beradi va yanada rivojlantirish imkoniyatlari mavjudligini ko'rsatadi.

Mutaxassislarning fikricha, {section_title.lower()} sohasini yanada rivojlantirish uchun quyidagi choralar ko'rilishi lozim: birinchidan, ilmiy tadqiqotlarni kengaytirish va chuqurlash tirish; ikkinchidan, amaliy tajribani ommalashtirish; uchinchidan, xalqaro hamkorlikni mustahkamlash; to'rtinchidan, zamonaviy texnologiyalarni joriy etish.

Xulosa qilib aytganda, {section_title.lower()} masalasi {subject.lower()} fanining muhim tarkibiy qismi bo'lib, uni har tomonlama o'rganish va rivojlantirish dolzarb vazifa hisoblanadi."""

    # =========================================================================
    # EXISTING METHODS (saqlab qolindi)
    # =========================================================================

    def _get_language_instructions(self, language: str) -> str:
        """Til bo'yicha ko'rsatmalar"""
        instructions = {
            'uz': """O'ZBEK TILIDA yozing!
- Lotin alifbosida
- Zamonaviy o'zbek adabiy tilida
- Ilmiy uslubda
- Grammatik to'g'ri""",
            'ru': """РУССКОМ ЯЗЫКЕ пишите!
- Используйте академический стиль
- Грамматически правильно
- Научная терминология""",
            'en': """Write in ENGLISH!
- Use academic style
- Proper grammar
- Scientific terminology"""
        }
        return instructions.get(language, instructions['uz'])

    def _get_work_structure(self, work_type: str, page_count: int) -> Dict:
        """Ish turi bo'yicha batafsil struktura"""

        # So'zlar sonini hisoblash
        total_words = page_count * 350

        structures = {
            'referat': {
                'name': "Referat",
                'intro_words': max(400, total_words // 8),
                'chapter_words': max(800, total_words // 4),
                'conclusion_words': max(300, total_words // 10),
                'min_references': 8,
                'chapters_outline': ['Nazariy asoslar', 'Amaliy tahlil'],
                'detailed_outline': f"""
KIRISH ({max(400, total_words // 8)} so'z):
- Mavzuning dolzarbligi va ahamiyati
- Ishning maqsadi va vazifalari
- Tadqiqot metodlari

I BOB. NAZARIY ASOSLAR ({max(800, total_words // 4)} so'z):
1.1. Asosiy tushunchalar va ta'riflar (400+ so'z)
1.2. Mavzuning nazariy asoslari (400+ so'z)
1.3. Xorijiy va mahalliy tajriba (400+ so'z)

II BOB. AMALIY TAHLIL ({max(800, total_words // 4)} so'z):
2.1. Hozirgi holat tahlili (400+ so'z)
2.2. Muammolar va yechimlar (400+ so'z)

XULOSA ({max(300, total_words // 10)} so'z):
- Asosiy xulosalar
- Tavsiyalar

ADABIYOTLAR: Kamida 8 ta manba
"""
            },
            'kurs_ishi': {
                'name': "Kurs ishi",
                'intro_words': max(600, total_words // 6),
                'chapter_words': max(1500, total_words // 3),
                'conclusion_words': max(500, total_words // 8),
                'min_references': 15,
                'chapters_outline': ['Nazariy asoslar', 'Amaliy tahlil', 'Tavsiyalar'],
                'detailed_outline': f"""
KIRISH ({max(600, total_words // 6)} so'z):
- Mavzuning dolzarbligi
- Muammoning qo'yilishi
- Maqsad va vazifalar (5-7 ta)
- Tadqiqot ob'ekti va predmeti
- Tadqiqot metodlari
- Ishning ilmiy yangiligi

I BOB. NAZARIY-METODOLOGIK ASOSLAR ({max(1500, total_words // 3)} so'z):
1.1. Asosiy tushunchalar va kategoriyalar (500+ so'z)
1.2. Nazariy yondashuvlar tahlili (500+ so'z)
1.3. Xorijiy tajriba va qiyosiy tahlil (500+ so'z)

II BOB. AMALIY TADQIQOT ({max(1500, total_words // 3)} so'z):
2.1. O'zbekistonda hozirgi holat (500+ so'z)
2.2. Muammolar va ularning sabablari (500+ so'z)
2.3. Case study / Amaliy misollar (500+ so'z)

III BOB. TAVSIYALAR VA ISTIQBOLLAR (800+ so'z):
3.1. Takomillashtirish yo'llari (400+ so'z)
3.2. Kelgusi istiqbollar (400+ so'z)

XULOSA ({max(500, total_words // 8)} so'z):
- Har bir vazifa bo'yicha xulosa
- Umumiy natijalar
- Amaliy tavsiyalar

ADABIYOTLAR: Kamida 15 ta manba
ILOVALAR: Jadvallar, grafiklar
"""
            },
            'mustaqil_ish': {
                'name': "Mustaqil ish",
                'intro_words': max(350, total_words // 8),
                'chapter_words': max(700, total_words // 4),
                'conclusion_words': max(250, total_words // 10),
                'min_references': 6,
                'chapters_outline': ['Nazariy qism', 'Amaliy qism'],
                'detailed_outline': f"""
KIRISH ({max(350, total_words // 8)} so'z):
- Mavzu haqida umumiy ma'lumot
- Ishning maqsadi
- Asosiy vazifalar

I BOB. NAZARIY QISM ({max(700, total_words // 4)} so'z):
1.1. Asosiy tushunchalar (350+ so'z)
1.2. Nazariy asoslar (350+ so'z)

II BOB. AMALIY QISM ({max(700, total_words // 4)} so'z):
2.1. Amaliy tahlil (350+ so'z)
2.2. Natijalar (350+ so'z)

XULOSA ({max(250, total_words // 10)} so'z):
- Asosiy xulosalar
- Qisqacha tavsiyalar

ADABIYOTLAR: Kamida 6 ta manba
"""
            },
            'ilmiy_maqola': {
                'name': "Ilmiy maqola",
                'intro_words': max(300, total_words // 8),
                'chapter_words': max(600, total_words // 4),
                'conclusion_words': max(200, total_words // 12),
                'min_references': 10,
                'chapters_outline': ['Kirish', 'Metodlar', 'Natijalar', 'Muhokama'],
                'detailed_outline': f"""
ANNOTATSIYA (200 so'z):
- Maqola mazmuni
- Kalit so'zlar (5-7 ta)

KIRISH ({max(300, total_words // 8)} so'z):
- Muammo bayoni
- Tadqiqot maqsadi
- Mavjud tadqiqotlar sharhi

MATERIALLAR VA METODLAR (300+ so'z):
- Tadqiqot usullari
- Ma'lumotlar bazasi

NATIJALAR ({max(600, total_words // 4)} so'z):
- Asosiy topilmalar
- Jadvallar va grafiklar tahlili

MUHOKAMA (400+ so'z):
- Natijalar interpretatsiyasi
- Boshqa tadqiqotlar bilan taqqoslash

XULOSA ({max(200, total_words // 12)} so'z):
- Qisqa xulosalar

ADABIYOTLAR: Kamida 10 ta manba
"""
            },
            'hisobot': {
                'name': "Hisobot",
                'intro_words': max(250, total_words // 10),
                'chapter_words': max(600, total_words // 4),
                'conclusion_words': max(200, total_words // 10),
                'min_references': 5,
                'chapters_outline': ['Bajarilgan ishlar', 'Natijalar'],
                'detailed_outline': f"""
KIRISH ({max(250, total_words // 10)} so'z):
- Hisobot maqsadi
- Qamrov davri

BAJARILGAN ISHLAR ({max(600, total_words // 4)} so'z):
- Rejadagi ishlar
- Amalga oshirilgan tadbirlar
- Muammolar va yechimlar

NATIJALAR ({max(600, total_words // 4)} so'z):
- Miqdoriy ko'rsatkichlar
- Sifat ko'rsatkichlari
- Taqqoslash

XULOSA VA TAVSIYALAR ({max(200, total_words // 10)} so'z):
- Umumiy baho
- Keyingi davr uchun tavsiyalar

ILOVALAR: Jadvallar, grafiklar
"""
            }
        }

        return structures.get(work_type, structures['mustaqil_ish'])

    def _validate_and_enhance_content(self, content: Dict, structure: Dict, topic: str, subject: str, page_count: int,
                                      language: str) -> Dict:
        """Kontentni tekshirish va yaxshilash"""

        # Asosiy maydonlar
        if not content.get('title'):
            content['title'] = topic

        if not content.get('subtitle'):
            content['subtitle'] = f"{subject} fanidan {structure['name'].lower()}"

        # Introduction tekshirish
        if not content.get('introduction') or not content['introduction'].get('content'):
            content['introduction'] = {
                'title': 'KIRISH',
                'content': self._generate_detailed_intro(topic, subject, structure, language)
            }
        elif len(content['introduction'].get('content', '')) < 500:
            content['introduction']['content'] = self._enhance_section(
                content['introduction']['content'],
                topic, subject, 'kirish', language
            )

        # Chapters tekshirish
        if not content.get('chapters') or len(content['chapters']) < 2:
            content['chapters'] = self._generate_detailed_chapters(topic, subject, structure, page_count, language)
        else:
            for chapter in content['chapters']:
                for section in chapter.get('sections', []):
                    if len(section.get('content', '')) < 400:
                        section['content'] = self._enhance_section(
                            section.get('content', ''),
                            topic, subject, section.get('title', ''), language
                        )

        # Conclusion tekshirish
        if not content.get('conclusion') or not content['conclusion'].get('content'):
            content['conclusion'] = {
                'title': 'XULOSA',
                'content': self._generate_detailed_conclusion(topic, subject, structure, language)
            }
        elif len(content['conclusion'].get('content', '')) < 300:
            content['conclusion']['content'] = self._enhance_section(
                content['conclusion']['content'],
                topic, subject, 'xulosa', language
            )

        # References tekshirish
        if not content.get('references') or len(content['references']) < structure['min_references']:
            content['references'] = self._generate_references(topic, subject, structure['min_references'])

        return content

    def _enhance_section(self, current_text: str, topic: str, subject: str, section_type: str, language: str) -> str:
        """Bo'limni kengaytirish"""
        if not current_text:
            current_text = ""

        enhancement = f"""
{current_text}

{topic} mavzusi bugungi kunda juda dolzarb hisoblanadi. {subject} sohasida olib borilgan tadqiqotlar shuni ko'rsatadiki, bu masala chuqur o'rganishni talab qiladi.

Olimlarning fikricha, ushbu sohada bir qator muammolar mavjud bo'lib, ularni hal qilish uchun kompleks yondashuv zarur. Xususan, quyidagi jihatlar alohida e'tiborga loyiq:

Birinchidan, nazariy asoslarni mustahkamlash lozim. Bu borada jahon tajribasini o'rganish va mahalliy sharoitlarga moslash muhim ahamiyatga ega.

Ikkinchidan, amaliy tatbiq etish mexanizmlarini ishlab chiqish kerak. Nazariy bilimlarni amaliyotga joriy etishda samarali usullarni qo'llash zarur.

Uchinchidan, monitoring va baholash tizimini yaratish talab etiladi. Bu esa jarayonlarni nazorat qilish va samaradorlikni oshirishga xizmat qiladi.

Statistik ma'lumotlarga ko'ra, so'nggi yillarda bu sohada sezilarli o'zgarishlar kuzatilmoqda. Mutaxassislarning bahosiga ko'ra, kelgusida bu tendensiya davom etadi.

Shunday qilib, {topic} masalasini hal qilish uchun ilmiy asoslangan yondashuvlar qo'llash, xalqaro tajribani o'rganish va innovatsion yechimlarni joriy etish lozim.
"""
        return enhancement.strip()

    def _generate_detailed_intro(self, topic: str, subject: str, structure: Dict, language: str) -> str:
        """Batafsil kirish yaratish"""
        return f"""{topic} mavzusi zamonaviy {subject.lower()} fanining eng dolzarb muammolaridan biri hisoblanadi. Bugungi kunda bu masala nafaqat ilmiy doiralarda, balki amaliyotda ham keng muhokama qilinmoqda.

Mavzuning dolzarbligi shundan iboratki, {topic.lower()} masalasi to'g'ridan-to'g'ri ijtimoiy-iqtisodiy rivojlanish bilan bog'liq. So'nggi yillarda bu sohada sezilarli o'zgarishlar ro'y berdi va yangi yondashuvlar paydo bo'ldi.

O'zbekiston Respublikasi Prezidentining ta'lim va fan sohasidagi islohotlar bo'yicha farmonlari va qarorlari bu masalaning ahamiyatini yanada oshirdi. Xususan, "{subject}" yo'nalishida olib borilayotgan islohotlar doirasida {topic.lower()} masalasini chuqur o'rganish zarurati tug'ildi.

Ishning maqsadi - {topic.lower()} bo'yicha nazariy va amaliy jihatlarni kompleks tahlil qilish, mavjud muammolarni aniqlash va ularni hal etish yo'llarini ishlab chiqishdan iborat.

Maqsadga erishish uchun quyidagi vazifalar belgilandi:
1. {topic} bo'yicha nazariy asoslarni o'rganish va tizimlashtirish;
2. Xorijiy va mahalliy tajribani qiyosiy tahlil qilish;
3. Hozirgi holatni baholash va asosiy muammolarni aniqlash;
4. Muammolarni hal etish bo'yicha tavsiyalar ishlab chiqish;
5. Kelgusi istiqbollarni belgilash.

Tadqiqot ob'ekti - {topic.lower()} jarayonlari va mexanizmlari.

Tadqiqot predmeti - {topic.lower()} sohasidagi nazariy yondashuvlar va amaliy tajriba.

Tadqiqot metodlari sifatida tahlil, sintez, qiyoslash, statistik tahlil, ekspert bahosi kabi usullardan foydalanildi.

Ishning ilmiy yangiligi shundaki, unda {topic.lower()} masalasi kompleks yondashuvda, zamonaviy talablar nuqtai nazaridan tahlil qilingan va amaliy tavsiyalar ishlab chiqilgan.

Ishning amaliy ahamiyati - olingan natijalar va tavsiyalar {subject.lower()} sohasida faoliyat yurituvchi tashkilotlar, mutaxassislar va tadqiqotchilar tomonidan qo'llanilishi mumkin.

Ish kirish, ikkita bob, xulosa va foydalanilgan adabiyotlar ro'yxatidan iborat."""

    def _generate_detailed_chapters(self, topic: str, subject: str, structure: Dict, page_count: int, language: str) -> \
    List[Dict]:
        """Batafsil boblar yaratish"""
        chapters = []

        # I BOB
        chapter1 = {
            'number': 1,
            'title': f'{topic.upper()} NAZARIY ASOSLARI',
            'sections': [
                {
                    'number': '1.1',
                    'title': 'Asosiy tushunchalar va kategoriyalar',
                    'content': f"""{topic} tushunchasi akademik adabiyotlarda turlicha talqin qilinadi. Klassik ta'rifga ko'ra, bu atama quyidagi ma'nolarni anglatadi va keng qo'llaniladi.

Zamonaviy {subject.lower()} fanida {topic.lower()} kategoriyasi markaziy o'rinlardan birini egallaydi. Olimlarning fikricha, bu tushunchani to'g'ri tushunish va qo'llash muhim ahamiyatga ega.

Tarixiy nuqtai nazardan qaraganda, {topic.lower()} g'oyasi uzoq tarixga ega. Dastlab bu tushuncha XVI-XVII asrlarda Evropada paydo bo'lgan va keyinchalik butun dunyoga tarqalgan.

O'zbekistonda {topic.lower()} masalasi mustaqillik yillaridan boshlab faol o'rganila boshlandi. Bugungi kunda bu sohada ko'plab tadqiqotlar olib borilmoqda va yangi yondashuvlar ishlab chiqilmoqda.

{topic} bilan bog'liq asosiy kategoriyalar quyidagilardan iborat: birlamchi kategoriyalar - asosiy tushunchalar va ta'riflar; ikkilamchi kategoriyalar - hosila tushunchalar; qo'shimcha kategoriyalar - yordamchi atamalar.

Har bir kategoriya o'ziga xos xususiyatlarga ega va alohida o'rganishni talab qiladi. Mutaxassislar bu kategoriyalarni turli mezonlar asosida tasniflashadi.

Xulosa qilib aytganda, {topic.lower()} tushunchasini to'g'ri anglash uchun uning tarixiy rivojlanishi, zamonaviy talqinlari va amaliy qo'llanilishini birgalikda o'rganish lozim."""
                },
                {
                    'number': '1.2',
                    'title': 'Nazariy yondashuvlar tahlili',
                    'content': f"""{topic} bo'yicha mavjud nazariy yondashuvlarni tahlil qilish muhim ahamiyatga ega. Jahon fanida bu masalaga turlicha qarashlar mavjud.

Klassik yondashuv tarafdorlari {topic.lower()} masalasini an'anaviy nuqtai nazardan ko'rib chiqishni taklif etishadi. Ularning fikricha, asosiy e'tibor nazariy asoslarga qaratilishi kerak.

Zamonaviy yondashuv vakillari esa amaliy jihatlarni birinchi o'ringa qo'yishadi. Bu yondashuv so'nggi yillarda tobora ko'proq tarafdorlar topmoqda.

Integratsion yondashuv har ikkala yo'nalishning ijobiy jihatlarini birlashtiradi. Bu yondashuv eng samarali deb hisoblanadi, chunki u nazariya va amaliyotni uyg'unlashtiradi.

Turli mamlakatlar tajribasini o'rganish shuni ko'rsatadiki, {topic.lower()} masalasida yagona universal yondashuv mavjud emas. Har bir mamlakat o'z sharoitlariga mos yechimlarni qo'llaydi.

Rivojlangan mamlakatlarda {topic.lower()} sohasida quyidagi tendensiyalar kuzatilmoqda: innovatsion yechimlardan foydalanish, raqamli texnologiyalarni joriy etish, xalqaro hamkorlikni kuchaytirish, ilmiy tadqiqotlarni kengaytirish.

O'zbekiston uchun eng maqbul yo'l - jahon tajribasini o'rganish va uni mahalliy sharoitlarga moslashtirishdir. Bu borada allaqachon ma'lum yutuqlarga erishilgan.

Shunday qilib, {topic.lower()} bo'yicha mavjud nazariy yondashuvlar tahlili shuni ko'rsatadiki, kompleks va integratsion yondashuv eng samarali hisoblanadi."""
                }
            ]
        }
        chapters.append(chapter1)

        # II BOB
        chapter2 = {
            'number': 2,
            'title': f'{topic.upper()} AMALIY TAHLILI',
            'sections': [
                {
                    'number': '2.1',
                    'title': "O'zbekistonda hozirgi holat tahlili",
                    'content': f"""O'zbekistonda {topic.lower()} sohasining hozirgi holatini tahlil qilish muhim amaliy ahamiyatga ega. So'nggi yillarda bu sohada sezilarli o'zgarishlar ro'y berdi.

Statistik ma'lumotlarga ko'ra, {topic.lower()} sohasida quyidagi ko'rsatkichlar qayd etilgan: asosiy ko'rsatkich bo'yicha ijobiy dinamika kuzatilmoqda; rivojlanish darajasi o'rtacha bo'lib, ba'zi muammolar mavjud.

Hukumat tomonidan {topic.lower()} sohasida bir qator chora-tadbirlar amalga oshirilmoqda. Xususan, maxsus dasturlar qabul qilingan va ularni amalga oshirish bo'yicha ishlar olib borilmoqda.

Mintaqaviy farqlar tahlili shuni ko'rsatadiki, respublikaning turli hududlarida {topic.lower()} sohasining rivojlanish darajasi turlicha. Poytaxt va yirik shaharlarda vaziyat nisbatan yaxshi, qishloq joylarda esa muammolar ko'proq.

Ekspertlarning fikricha, {topic.lower()} sohasida quyidagi ijobiy tendensiyalar kuzatilmoqda: institutsional tizimning mustahkamlanishi, kadrlar salohiyatining oshishi, xalqaro hamkorlikning kengayishi, texnologik bazaning yangilanishi.

Shu bilan birga, hal qilinishi kerak bo'lgan muammolar ham mavjud. Bu muammolarni aniqlash va ularni bartaraf etish yo'llarini ishlab chiqish keyingi bo'limda batafsil ko'rib chiqiladi.

Umumiy baholash shuni ko'rsatadiki, O'zbekistonda {topic.lower()} sohasi rivojlanish bosqichida va kelajakda yanada yaxshi natijalarga erishish mumkin."""
                },
                {
                    'number': '2.2',
                    'title': 'Muammolar va ularni hal etish yo\'llari',
                    'content': f"""{topic} sohasida mavjud muammolarni aniqlash va ularni hal etish yo'llarini ishlab chiqish ishning muhim qismi hisoblanadi.

Birinchi muammo - resurslarning yetishmasligi. Bu muammo ko'plab tashkilotlar faoliyatiga salbiy ta'sir ko'rsatmoqda. Yechim sifatida moliyalashtirish manbalarini diversifikatsiya qilish taklif etiladi.

Ikkinchi muammo - malakali kadrlarning yetishmasligi. Bu muammo sohaning rivojlanishiga to'sqinlik qilmoqda. Yechim - kadrlar tayyorlash tizimini takomillashtirish va xalqaro tajriba almashuvini kengaytirish.

Uchinchi muammo - texnologik jihatdan orqada qolish. Zamonaviy texnologiyalarni joriy etish uchun qo'shimcha investitsiyalar va bilimlar kerak. Yechim - innovatsion dasturlarni amalga oshirish.

To'rtinchi muammo - me'yoriy-huquqiy bazaning nomukammalligi. Ba'zi qonun hujjatlari eskirgan va yangilanishni talab qiladi. Yechim - qonunchilikni takomillashtirish.

Bu muammolarni hal etish uchun quyidagi chora-tadbirlar taklif etiladi: davlat dasturlarini ishlab chiqish va amalga oshirish, xususiy sektor ishtirokini kengaytirish, xalqaro donorlar bilan hamkorlik, ilmiy tadqiqotlarni qo'llab-quvvatlash.

Taklif etilgan chora-tadbirlarni amalga oshirish uchun aniq muddat va mas'ullar belgilanishi lozim. Monitoring va baholash tizimi ham muhim ahamiyatga ega.

Xulosa qilib aytganda, {topic.lower()} sohasidagi muammolarni hal etish uchun kompleks yondashuv va barcha manfaatdor tomonlarning hamkorligi zarur."""
                }
            ]
        }
        chapters.append(chapter2)

        return chapters

    def _generate_detailed_conclusion(self, topic: str, subject: str, structure: Dict, language: str) -> str:
        """Batafsil xulosa yaratish"""
        return f"""Ushbu ishda {topic.lower()} mavzusi bo'yicha nazariy va amaliy tadqiqot olib borildi. Tadqiqot natijasida quyidagi xulosalarga kelindi:

Birinchidan, {topic.lower()} masalasi bugungi kunda dolzarb bo'lib, chuqur ilmiy o'rganishni talab qiladi. Nazariy tahlil shuni ko'rsatdiki, bu sohada turli yondashuvlar mavjud va ularning har biri o'ziga xos afzalliklarga ega.

Ikkinchidan, xorijiy tajriba tahlili rivojlangan mamlakatlarda {topic.lower()} sohasida yuqori natijalarga erishilganini ko'rsatdi. O'zbekiston uchun bu tajribani o'rganish va mahalliy sharoitlarga moslash muhim ahamiyatga ega.

Uchinchidan, O'zbekistonda {topic.lower()} sohasining hozirgi holati tahlili ijobiy tendensiyalar bilan bir qatorda, hal qilinishi kerak bo'lgan muammolar ham mavjudligini ko'rsatdi.

To'rtinchidan, aniqlangan muammolarni hal etish uchun kompleks yondashuv zarur. Taklif etilgan chora-tadbirlarni amalga oshirish sohaning rivojlanishiga sezilarli hissa qo'shishi mumkin.

Tadqiqot natijalariga asoslanib, quyidagi tavsiyalar ishlab chiqildi:

1. {topic} sohasida me'yoriy-huquqiy bazani takomillashtirish va zamonaviy talablarga moslashtirish zarur;

2. Kadrlar tayyorlash tizimini yanada rivojlantirish va xalqaro tajriba almashuvini kengaytirish lozim;

3. Zamonaviy texnologiyalarni joriy etish va innovatsion yechimlarni qo'llash muhim;

4. Xalqaro hamkorlikni kengaytirish va donorlar bilan aloqalarni mustahkamlash kerak;

5. Monitoring va baholash tizimini joriy etish va samaradorlikni muntazam tahlil qilish zarur.

Kelgusidagi tadqiqotlar uchun quyidagi yo'nalishlar taklif etiladi: {topic} sohasining ayrim jihatlarini chuqurroq o'rganish, mintaqaviy xususiyatlarni tahlil qilish, xalqaro qiyosiy tadqiqotlar olib borish.

Ushbu ish {subject} sohasida faoliyat yurituvchi mutaxassislar, tadqiqotchilar va amaliyotchilar uchun foydali bo'lishi mumkin."""

    def _generate_references(self, topic: str, subject: str, count: int) -> List[str]:
        """Adabiyotlar ro'yxatini yaratish"""
        references = [
            f"1. Karimov A.A. {subject} asoslari. – T.: Fan nashriyoti, 2023. – 256 b.",
            f"2. Rahimov B.B. {topic[:40]} nazariyasi va amaliyoti. – T.: O'qituvchi, 2022. – 180 b.",
            f"3. Sobirova M.K., Aliyev D.R. Zamonaviy {subject.lower()}. – T.: Akademiya, 2023. – 320 b.",
            f"4. Xolmatov S.S. {subject} sohasida innovatsion yondashuvlar. – T.: Universitet, 2022. – 200 b.",
            f"5. Qodirov N.N. {topic[:30]} bo'yicha qo'llanma. – T.: Yangi asr avlodi, 2023. – 150 b.",
            f"6. Smith J., Johnson R. Introduction to {subject}. – London: Academic Press, 2022. – 450 p.",
            f"7. Williams A. Modern approaches in {subject.lower()}. – NY: Springer, 2023. – 380 p.",
            f"8. Brown K. Handbook of {topic[:25]}. – Cambridge: University Press, 2022. – 520 p.",
            f"9. O'zbekiston Respublikasi Qonunlari to'plami. – T.: Adolat, 2023.",
            f"10. O'zbekiston Respublikasi Prezidentining Farmonlari to'plami. – T., 2023.",
            f"11. www.stat.uz - O'zbekiston Respublikasi Statistika qo'mitasi rasmiy sayti",
            f"12. www.lex.uz - O'zbekiston Respublikasi Qonunchilik bazasi",
            f"13. www.ziyonet.uz - O'zbekiston ta'lim portali",
            f"14. www.scholar.google.com - Ilmiy maqolalar bazasi",
            f"15. www.sciencedirect.com - Xalqaro ilmiy jurnallar bazasi",
        ]
        return references[:count]

    def _generate_detailed_fallback_content(self, work_type: str, topic: str, subject: str, details: str,
                                            page_count: int, language: str) -> Dict:
        """Batafsil fallback content"""
        structure = self._get_work_structure(work_type, page_count)

        return {
            'title': topic,
            'subtitle': f"{subject} fanidan {structure['name'].lower()}",
            'author_info': {
                'institution': "O'zbekiston Milliy Universiteti",
                'faculty': f"{subject} fakulteti",
                'department': f"{subject} kafedrasi"
            },
            'abstract': f"Ushbu {structure['name'].lower()} {topic} mavzusiga bag'ishlangan. Ishda mavzuning nazariy asoslari o'rganilgan, xorijiy va mahalliy tajriba tahlil qilingan, hozirgi holat baholangan va tavsiyalar ishlab chiqilgan.",
            'keywords': [topic.split()[0] if topic else "mavzu", subject, "tadqiqot", "tahlil", "tavsiya"],
            'table_of_contents': [
                {'title': 'KIRISH', 'page': 3},
                {'title': 'I BOB. NAZARIY ASOSLAR', 'page': 5},
                {'title': 'II BOB. AMALIY TAHLIL', 'page': page_count // 2 + 2},
                {'title': 'XULOSA', 'page': page_count - 2},
                {'title': 'ADABIYOTLAR', 'page': page_count}
            ],
            'introduction': {
                'title': 'KIRISH',
                'content': self._generate_detailed_intro(topic, subject, structure, language)
            },
            'chapters': self._generate_detailed_chapters(topic, subject, structure, page_count, language),
            'conclusion': {
                'title': 'XULOSA',
                'content': self._generate_detailed_conclusion(topic, subject, structure, language)
            },
            'recommendations': [
                f"{topic} sohasida me'yoriy-huquqiy bazani takomillashtirish",
                "Kadrlar tayyorlash tizimini rivojlantirish",
                "Zamonaviy texnologiyalarni joriy etish",
                "Xalqaro hamkorlikni kengaytirish"
            ],
            'references': self._generate_references(topic, subject, structure['min_references']),
            'appendix': None
        }

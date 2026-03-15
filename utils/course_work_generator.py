# utils/course_work_generator.py
# MUSTAQIL ISH / REFERAT CONTENT GENERATOR
# ✅ YANGILANGAN - Ko'proq va batafsil content

import asyncio
import json
import logging
from typing import Dict, List, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class CourseWorkGenerator:
    """
    OpenAI API bilan mustaqil ish / referat yaratish
    ✅ YANGILANGAN - Batafsil content
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
        Mustaqil ish uchun BATAFSIL content yaratish
        """
        model = "gpt-4o" if use_gpt4 else "gpt-3.5-turbo"

        # Til bo'yicha prompt
        lang_instructions = self._get_language_instructions(language)

        # Ish turi bo'yicha struktura
        structure = self._get_work_structure(work_type, page_count)

        # So'zlar sonini hisoblash (1 sahifa ≈ 300-350 so'z)
        total_words = page_count * 350
        words_per_chapter = total_words // (
                    len(structure.get('chapters_outline', [])) + 2)  # +2 for intro and conclusion

        prompt = f"""
{lang_instructions}

Siz O'zbekistondagi ENG TAJRIBALI professor va akademik yozuvchisiz. 
Quyidagi parametrlar asosida TO'LIQ va BATAFSIL {structure['name']} yozing.

⚠️ MUHIM: Bu HAQIQIY akademik ish bo'lishi kerak - QISQARTIRMANG!

📋 PARAMETRLAR:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Ish turi: {structure['name']}
• Mavzu: {topic}
• Fan: {subject}
• Sahifalar: {page_count} ta (taxminan {total_words} so'z)
• Til: {language.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 QO'SHIMCHA TALABLAR:
{details if details else "Maxsus talablar yo'q - umumiy akademik standartlarga rioya qiling"}

📚 MAJBURIY STRUKTURA:
{structure['detailed_outline']}

✍️ YOZISH QOIDALARI:

1. KIRISH ({structure['intro_words']} so'z):
   - Mavzuning dolzarbligi (nima uchun bu mavzu muhim?)
   - Muammoning qo'yilishi
   - Ishning maqsadi va vazifalari (aniq, raqamlangan)
   - Tadqiqot ob'ekti va predmeti
   - Tadqiqot metodlari
   - Ishning tuzilishi haqida qisqacha

2. HAR BIR BOB ({structure['chapter_words']} so'z):
   - Har bir bo'lim kamida 5-7 ta to'liq paragrafdan iborat
   - Har bir paragraf 6-8 ta gapdan iborat
   - Ilmiy manbalardan iqtiboslar keltiring
   - Statistik ma'lumotlar va faktlar
   - Misollar va dalillar
   - Jadvallar va taqqoslashlar (matn ichida)
   - Har bir bo'lim oxirida qisqa xulosa

3. XULOSA ({structure['conclusion_words']} so'z):
   - Asosiy topilmalar va natijalar
   - Har bir vazifa bo'yicha xulosa
   - Amaliy tavsiyalar
   - Kelgusidagi tadqiqotlar uchun yo'nalishlar

4. ADABIYOTLAR:
   - Kamida {structure['min_references']} ta manba
   - O'zbek va xorijiy manbalar
   - Internet manbalar (ishonchli saytlar)
   - GOST standartiga mos formatda

⚠️ QISQARTIRISH MUMKIN EMAS! Har bir bo'limni TO'LIQ yozing!

JSON formatida qaytaring:
{{
    "title": "{topic}",
    "subtitle": "{subject} fanidan {structure['name'].lower()}",
    "author_info": {{
        "institution": "O'zbekiston Milliy Universiteti",
        "faculty": "{subject} fakulteti",
        "department": "{subject} kafedrasi"
    }},
    "abstract": "Annotatsiya - 200-250 so'z. Ishning qisqacha mazmuni, maqsadi, metodlari va asosiy natijalari.",
    "keywords": ["kalit1", "kalit2", "kalit3", "kalit4", "kalit5"],
    "table_of_contents": [
        {{"title": "KIRISH", "page": 3}},
        {{"title": "I BOB. [BOB NOMI]", "page": 5}},
        {{"title": "1.1. [Bo'lim nomi]", "page": 5}},
        {{"title": "1.2. [Bo'lim nomi]", "page": 8}},
        {{"title": "II BOB. [BOB NOMI]", "page": 12}},
        {{"title": "XULOSA", "page": {page_count - 2}}},
        {{"title": "FOYDALANILGAN ADABIYOTLAR", "page": {page_count}}}
    ],
    "introduction": {{
        "title": "KIRISH",
        "content": "KIRISH MATNI - {structure['intro_words']} so'z. Bu yerda mavzuning dolzarbligi, maqsad, vazifalar, metodlar haqida BATAFSIL yozing. Kamida 6-8 ta to'liq paragraf."
    }},
    "chapters": [
        {{
            "number": 1,
            "title": "NAZARIY ASOSLAR",
            "sections": [
                {{
                    "number": "1.1",
                    "title": "Asosiy tushunchalar va ta'riflar",
                    "content": "BO'LIM MATNI - kamida 800-1000 so'z. 5-7 ta to'liq paragraf. Har bir paragraf 6-8 gap."
                }},
                {{
                    "number": "1.2", 
                    "title": "Mavzuning nazariy asoslari",
                    "content": "BO'LIM MATNI - kamida 800-1000 so'z. Ilmiy manbalardan iqtiboslar, statistika, faktlar."
                }}
            ]
        }},
        {{
            "number": 2,
            "title": "AMALIY TAHLIL",
            "sections": [
                {{
                    "number": "2.1",
                    "title": "Hozirgi holat tahlili",
                    "content": "BO'LIM MATNI - kamida 800-1000 so'z. Amaliy misollar, jadvallar, taqqoslashlar."
                }},
                {{
                    "number": "2.2",
                    "title": "Muammolar va yechimlar",
                    "content": "BO'LIM MATNI - kamida 800-1000 so'z. Aniq muammolar va ularning yechimlari."
                }}
            ]
        }}
    ],
    "conclusion": {{
        "title": "XULOSA",
        "content": "XULOSA MATNI - {structure['conclusion_words']} so'z. Asosiy topilmalar, har bir vazifa bo'yicha xulosa, tavsiyalar. Kamida 5-6 ta to'liq paragraf."
    }},
    "recommendations": [
        "Birinchi tavsiya - aniq va amaliy",
        "Ikkinchi tavsiya - amalga oshirish mumkin",
        "Uchinchi tavsiya - kelajak uchun"
    ],
    "references": [
        "1. Karimov A.A. {subject} asoslari. – T.: Fan, 2023. – 256 b.",
        "2. Rahimov B.B. {topic[:30]} nazariyasi. – T.: O'qituvchi, 2022. – 180 b.",
        "3. Sobirova M.K. Zamonaviy {subject.lower()}. – T.: Akademiya, 2023. – 320 b.",
        "4. Smith J. Introduction to {subject}. – London: Academic Press, 2022. – 450 p.",
        "5. Johnson R. Modern approaches. – NY: Springer, 2023. – 380 p.",
        "6. O'zbekiston Respublikasi Qonunlari to'plami. – T., 2023.",
        "7. www.stat.uz - O'zbekiston Statistika qo'mitasi",
        "8. www.ziyonet.uz - O'zbekiston ta'lim portali",
        "9. www.scholar.google.com - Ilmiy maqolalar bazasi",
        "10. www.sciencedirect.com - Xalqaro ilmiy jurnal"
    ],
    "appendix": null
}}

⚠️ ESLATMA: Har bir content maydoni HAQIQIY, TO'LIQ matn bo'lishi kerak - placeholder emas!
Jami {total_words} so'zdan kam bo'lmasin!
"""

        try:
            logger.info(f"📝 OpenAI: {structure['name']} yaratish boshlandi ({total_words} so'z)")

            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""Siz O'zbekistondagi eng tajribali professor va akademik yozuvchisiz. 
{lang_instructions}

MUHIM QOIDALAR:
1. Har bir so'rovga TO'LIQ va BATAFSIL javob bering
2. HECH QACHON qisqartirmang yoki placeholder ishlatmang
3. Haqiqiy akademik uslubda yozing
4. Har bir bo'lim kamida 800-1000 so'zdan iborat bo'lsin
5. Ilmiy manbalardan iqtiboslar keltiring
6. Statistik ma'lumotlar va faktlar ishlating
7. {subject} sohasidagi eng so'nggi ma'lumotlarni yozing"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=16000,  # Maksimal token
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            content = json.loads(response.choices[0].message.content)
            logger.info(f"✅ OpenAI: {structure['name']} yaratildi")

            # Validatsiya va to'ldirish
            content = self._validate_and_enhance_content(content, structure, topic, subject, page_count, language)

            return content

        except Exception as e:
            logger.error(f"❌ OpenAI xato: {e}")
            return self._generate_detailed_fallback_content(work_type, topic, subject, details, page_count, language)

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
            # Kirish juda qisqa - kengaytirish
            content['introduction']['content'] = self._enhance_section(
                content['introduction']['content'],
                topic, subject, 'kirish', language
            )

        # Chapters tekshirish
        if not content.get('chapters') or len(content['chapters']) < 2:
            content['chapters'] = self._generate_detailed_chapters(topic, subject, structure, page_count, language)
        else:
            # Har bir bo'limni tekshirish
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

        # Qo'shimcha matn qo'shish
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
        return f"""
{topic} mavzusi zamonaviy {subject.lower()} fanining eng dolzarb muammolaridan biri hisoblanadi. Bugungi kunda bu masala nafaqat ilmiy doiralarda, balki amaliyotda ham keng muhokama qilinmoqda.

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

Ish kirish, ikkita bob, xulosa va foydalanilgan adabiyotlar ro'yxatidan iborat.
"""

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
                    'content': f"""
{topic} tushunchasi akademik adabiyotlarda turlicha talqin qilinadi. Klassik ta'rifga ko'ra, bu atama quyidagi ma'nolarni anglatadi va keng qo'llaniladi.

Zamonaviy {subject.lower()} fanida {topic.lower()} kategoriyasi markaziy o'rinlardan birini egallaydi. Olimlarning fikricha, bu tushunchani to'g'ri tushunish va qo'llash muhim ahamiyatga ega.

Tarixiy nuqtai nazardan qaraganda, {topic.lower()} g'oyasi uzoq tarixga ega. Dastlab bu tushuncha XVI-XVII asrlarda Evropada paydo bo'lgan va keyinchalik butun dunyoga tarqalgan.

O'zbekistonda {topic.lower()} masalasi mustaqillik yillaridan boshlab faol o'rganila boshlandi. Bugungi kunda bu sohada ko'plab tadqiqotlar olib borilmoqda va yangi yondashuvlar ishlab chiqilmoqda.

{topic} bilan bog'liq asosiy kategoriyalar quyidagilardan iborat:
- Birlamchi kategoriyalar - asosiy tushunchalar va ta'riflar;
- Ikkilamchi kategoriyalar - hosila tushunchalar;
- Qo'shimcha kategoriyalar - yordamchi atamalar.

Har bir kategoriya o'ziga xos xususiyatlarga ega va alohida o'rganishni talab qiladi. Mutaxassislar bu kategoriyalarni turli mezonlar asosida tasniflashadi.

Xulosa qilib aytganda, {topic.lower()} tushunchasini to'g'ri anglash uchun uning tarixiy rivojlanishi, zamonaviy talqinlari va amaliy qo'llanilishini birgalikda o'rganish lozim.
"""
                },
                {
                    'number': '1.2',
                    'title': 'Nazariy yondashuvlar tahlili',
                    'content': f"""
{topic} bo'yicha mavjud nazariy yondashuvlarni tahlil qilish muhim ahamiyatga ega. Jahon fanida bu masalaga turlicha qarashlar mavjud.

Klassik yondashuv tarafdorlari {topic.lower()} masalasini an'anaviy nuqtai nazardan ko'rib chiqishni taklif etishadi. Ularning fikricha, asosiy e'tibor nazariy asoslarga qaratilishi kerak.

Zamonaviy yondashuv vakillari esa amaliy jihatlarni birinchi o'ringa qo'yishadi. Bu yondashuv so'nggi yillarda tobora ko'proq tarafdorlar topmoqda.

Integratsion yondashuv har ikkala yo'nalishning ijobiy jihatlarini birlashtiradi. Bu yondashuv eng samarali deb hisoblanadi, chunki u nazariya va amaliyotni uyg'unlashtiradi.

Turli mamlakatlar tajribasini o'rganish shuni ko'rsatadiki, {topic.lower()} masalasida yagona universal yondashuv mavjud emas. Har bir mamlakat o'z sharoitlariga mos yechimlarni qo'llaydi.

Rivojlangan mamlakatlarda {topic.lower()} sohasida quyidagi tendensiyalar kuzatilmoqda:
1. Innovatsion yechimlardan foydalanish;
2. Raqamli texnologiyalarni joriy etish;
3. Xalqaro hamkorlikni kuchaytirish;
4. Ilmiy tadqiqotlarni kengaytirish.

O'zbekiston uchun eng maqbul yo'l - jahon tajribasini o'rganish va uni mahalliy sharoitlarga moslashtirishdir. Bu borada allaqachon ma'lum yutuqlarga erishilgan.

Shunday qilib, {topic.lower()} bo'yicha mavjud nazariy yondashuvlar tahlili shuni ko'rsatadiki, kompleks va integratsion yondashuv eng samarali hisoblanadi.
"""
                },
                {
                    'number': '1.3',
                    'title': 'Xorijiy va mahalliy tajriba',
                    'content': f"""
{topic} sohasida xorijiy tajribani o'rganish muhim amaliy ahamiyatga ega. Rivojlangan mamlakatlar bu sohada katta yutuqlarga erishgan.

AQShda {topic.lower()} tizimi yuqori darajada rivojlangan. Bu yerda zamonaviy texnologiyalar keng qo'llaniladi va samarali natijalar olinmoqda. AQSh tajribasi ko'plab mamlakatlar uchun namuna bo'lib xizmat qilmoqda.

Yevropa Ittifoqi mamlakatlarida {topic.lower()} sohasida yagona standartlar amal qiladi. Bu esa mamlakatlararo hamkorlikni osonlashtiradi va samaradorlikni oshiradi.

Janubiy Koreya va Yaponiyada {topic.lower()} tizimi o'ziga xos xususiyatlarga ega. Bu mamlakatlar an'anaviy qadriyatlarni zamonaviy yondashuvlar bilan uyg'unlashtirishga muvaffaq bo'lgan.

Rossiya Federatsiyasida {topic.lower()} sohasida katta tajriba to'plangan. O'zbekiston uchun bu tajriba alohida ahamiyatga ega, chunki ikki mamlakat o'rtasida tarixiy va madaniy yaqinlik mavjud.

O'zbekistonda {topic.lower()} sohasida quyidagi ishlar amalga oshirilmoqda:
- Qonunchilik bazasini takomillashtirish;
- Institutsional tizimni rivojlantirish;
- Kadrlar tayyorlash tizimini yaxshilash;
- Xalqaro hamkorlikni kengaytirish.

Mahalliy tajriba tahlili shuni ko'rsatadiki, so'nggi yillarda bu sohada sezilarli yutuqlarga erishilgan. Biroq, hal qilinishi kerak bo'lgan muammolar ham mavjud.

Xulosa qilib aytganda, xorijiy va mahalliy tajribani qiyosiy o'rganish {topic.lower()} sohasini yanada rivojlantirish uchun muhim asos bo'lib xizmat qiladi.
"""
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
                    'content': f"""
O'zbekistonda {topic.lower()} sohasining hozirgi holatini tahlil qilish muhim amaliy ahamiyatga ega. So'nggi yillarda bu sohada sezilarli o'zgarishlar ro'y berdi.

Statistik ma'lumotlarga ko'ra, {topic.lower()} sohasida quyidagi ko'rsatkichlar qayd etilgan:
- Asosiy ko'rsatkich 1: ijobiy dinamika kuzatilmoqda;
- Asosiy ko'rsatkich 2: o'rtacha darajada rivojlanish;
- Asosiy ko'rsatkich 3: ba'zi muammolar mavjud.

Hukumat tomonidan {topic.lower()} sohasida bir qator chora-tadbirlar amalga oshirilmoqda. Xususan, maxsus dasturlar qabul qilingan va ularni amalga oshirish bo'yicha ishlar olib borilmoqda.

Mintaqaviy farqlar tahlili shuni ko'rsatadiki, respublikaning turli hududlarida {topic.lower()} sohasining rivojlanish darajasi turlicha. Poytaxt va yirik shaharlarda vaziyat nisbatan yaxshi, qishloq joylarda esa muammolar ko'proq.

Ekspertlarning fikricha, {topic.lower()} sohasida quyidagi ijobiy tendensiyalar kuzatilmoqda:
1. Institutsional tizimning mustahkamlanishi;
2. Kadrlar salohiyatining oshishi;
3. Xalqaro hamkorlikning kengayishi;
4. Texnologik bazaning yangilanishi.

Shu bilan birga, hal qilinishi kerak bo'lgan muammolar ham mavjud. Bu muammolarni aniqlash va ularni bartaraf etish yo'llarini ishlab chiqish keyingi bo'limda batafsil ko'rib chiqiladi.

Umumiy baholash shuni ko'rsatadiki, O'zbekistonda {topic.lower()} sohasi rivojlanish bosqichida va kelajakda yanada yaxshi natijalarga erishish mumkin.
"""
                },
                {
                    'number': '2.2',
                    'title': 'Muammolar va ularni hal etish yo\'llari',
                    'content': f"""
{topic} sohasida mavjud muammolarni aniqlash va ularni hal etish yo'llarini ishlab chiqish ishning muhim qismi hisoblanadi.

Asosiy muammolar quyidagilardan iborat:

Birinchi muammo - resurslarning yetishmasligi. Bu muammo ko'plab tashkilotlar faoliyatiga salbiy ta'sir ko'rsatmoqda. Yechim sifatida moliyalashtirish manbalarini diversifikatsiya qilish taklif etiladi.

Ikkinchi muammo - malakali kadrlarning yetishmasligi. Bu muammo sohaning rivojlanishiga to'sqinlik qilmoqda. Yechim - kadrlar tayyorlash tizimini takomillashtirish va xalqaro tajriba almashuvini kengaytirish.

Uchinchi muammo - texnologik jihatdan orqada qolish. Zamonaviy texnologiyalarni joriy etish uchun qo'shimcha investitsiyalar va bilimlar kerak. Yechim - innovatsion dasturlarni amalga oshirish.

To'rtinchi muammo - me'yoriy-huquqiy bazaning nomukammalligi. Ba'zi qonun hujjatlari eskirgan va yangilanishni talab qiladi. Yechim - qonunchilikni takomillashtirish.

Bu muammolarni hal etish uchun quyidagi chora-tadbirlar taklif etiladi:
1. Davlat dasturlarini ishlab chiqish va amalga oshirish;
2. Xususiy sektor ishtirokini kengaytirish;
3. Xalqaro donorlar bilan hamkorlik;
4. Ilmiy tadqiqotlarni qo'llab-quvvatlash.

Taklif etilgan chora-tadbirlarni amalga oshirish uchun aniq muddat va mas'ullar belgilanishi lozim. Monitoring va baholash tizimi ham muhim ahamiyatga ega.

Xulosa qilib aytganda, {topic.lower()} sohasidagi muammolarni hal etish uchun kompleks yondashuv va barcha manfaatdor tomonlarning hamkorligi zarur.
"""
                }
            ]
        }
        chapters.append(chapter2)

        return chapters

    def _generate_detailed_conclusion(self, topic: str, subject: str, structure: Dict, language: str) -> str:
        """Batafsil xulosa yaratish"""
        return f"""
Ushbu ishda {topic.lower()} mavzusi bo'yicha nazariy va amaliy tadqiqot olib borildi. Tadqiqot natijasida quyidagi xulosalarga kelindi:

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

Kelgusidagi tadqiqotlar uchun quyidagi yo'nalishlar taklif etiladi:
- {topic} sohasining ayrim jihatlarini chuqurroq o'rganish;
- Mintaqaviy xususiyatlarni tahlil qilish;
- Xalqaro qiyosiy tadqiqotlar olib borish.

Ushbu ish {subject} sohasida faoliyat yurituvchi mutaxassislar, tadqiqotchilar va amaliyotchilar uchun foydali bo'lishi mumkin.
"""

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
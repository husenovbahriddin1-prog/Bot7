import json
from openai import AsyncOpenAI
from config import settings

client = AsyncOpenAI(
    api_key=settings.gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

SYSTEM_PROMPT = """
Siz BuxPrime uchun Telegram guruhlaridagi ish jarayonini tahlil qiluvchi nazoratchisiz.
Faqat xabarlarda aniq ko‘rinadigan dalillarga asoslaning. Taxminni fakt deb yozmang.
Bir masala keyingi xabarlarda davom etsa, yangi muammo ochmang, mavjudini update qiling.
Muammo faqat aniq bajarilgani yoki bartaraf etilgani aytilsa resolve bo‘ladi.
Pul o‘tkazildi degani material yetkazildi degani emas.
Mas’ul faqat o‘zi vazifani olganini aytsa yoki aniq tayinlangan bo‘lsa belgilanadi.
Savolga javob berilganini faqat mazmunan javob bo‘lsa belgilang.
Xodim samaradorligi haqida xulosa qilishda yetarli dalil bo‘lmasa reyting bermang.
Javobni faqat quyidagi JSON formatida qaytaring:
{
  "issues": [{"action": "open|update|resolve", "title": "qisqa nom", "details": "tafsilot", "raised_by": "ism yoki null", "responsible": "ism yoki null"}],
  "questions": [{"action": "ask|answer", "question": "savol", "question_hint": "javob berilgan savolni topish uchun kalit", "asked_by": "ism yoki null", "answered_by": "ism yoki null"}],
  "tasks": [{"action": "create|complete", "title": "vazifa", "title_hint": "bajarilgan vazifani topish kaliti", "responsible": "ism yoki null"}],
  "note": "xabar tahlili haqida qisqa izoh"
}
Agar tegishli hodisa bo‘lmasa, massivlarni bo‘sh qaytaring.
"""


async def analyze_message(group_title, author, current_text, context):
    history = "\n".join(f"{m['user_name']}: {m['body']}" for m in context[-20:])
    user_prompt = (
        f"Guruh: {group_title}\nJoriy xabar muallifi: {author}\n"
        f"Oldingi xabarlar:\n{history}\n\nYangi xabar:\n{author}: {current_text}"
    )
    response = await client.chat.completions.create(
        model=settings.gemini_model,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return json.loads(response.choices[0].message.content or "{}")

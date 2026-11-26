import html
from db import Database


async def build_daily_report(db: Database, days=1):
    groups, issues, questions, solved_count, tasks = await db.report_data(days)
    if not groups:
        return "Hozircha bot kuzatayotgan guruhlar yo‘q."

    title = "SO‘NGGI 7 KUN" if days == 7 else "BUGUNGI HOLAT"

    summary_table = (
        "+-------------------------+--------+\n"
        "| Ko'rsatkich             | Soni   |\n"
        "+-------------------------+--------+\n"
        f"| Ulangan guruhlar        | {len(groups):<6} |\n"
        f"| Ochiq muammolar         | {len(issues):<6} |\n"
        f"| Javobsiz savollar       | {len(questions):<6} |\n"
        f"| Hal qilingan muammolar  | {solved_count:<6} |\n"
        "+-------------------------+--------+"
    )

    group_rows = [
        "+----------------------+-------+-------+",
        "| Guruh nomi           | Muam. | Savol |",
        "+----------------------+-------+-------+",
    ]
    for g in groups:
        g_issues = [x for x in issues if x["chat_id"] == g["chat_id"]]
        g_questions = [x for x in questions if x["chat_id"] == g["chat_id"]]
        g_name = html.escape(g["title"][:20])
        group_rows.append(
            f"| {g_name:<20} | {len(g_issues):<5} | {len(g_questions):<5} |"
        )
    group_rows.append("+----------------------+-------+-------+")

    lines = [
        f"<b>📊 {title}</b>",
        f"<pre>{summary_table}</pre>",
        "<b>Guruhlar kesimida:</b>",
        "<pre>" + "\n".join(group_rows) + "</pre>",
    ]

    if issues:
        lines.append("\n<b>⚠️ Ochiq muammolar:</b>")
        for x in issues[:15]:
            grp = html.escape(x["group_title"])
            ttl = html.escape(x["title"])
            resp = html.escape(x["responsible"] or "aniqlanmagan")
            lines.append(f"• <b>{grp}</b>: {ttl} — <i>mas’ul: {resp}</i>")

    if questions:
        lines.append("\n<b>❓ Javobsiz savollar:</b>")
        for x in questions[:15]:
            grp = html.escape(x["group_title"])
            qst = html.escape(x["question"])
            ask = html.escape(x["asked_by"] or "noma’lum")
            lines.append(f"• <b>{grp}</b>: {qst} — <i>so‘ragan: {ask}</i>")

    if tasks:
        lines.append("\n<b>📌 Bajarilishi kutilayotgan vazifalar:</b>")
        for x in tasks[:15]:
            grp = html.escape(x["group_title"])
            ttl = html.escape(x["title"])
            resp = html.escape(x["responsible"] or "mas’ul aniqlanmagan")
            lines.append(f"• <b>{grp}</b>: {ttl} — <i>{resp}</i>")

    lines.append(
        "\n<i>Eslatma: AI xulosalari guruh xabarlaridagi dalillarga asoslanadi. "
        "Noaniq mas’ul yoki yechim tasdiqlanmagan deb ko‘rsatilishi kerak.</i>"
    )
    return "\n".join(lines)

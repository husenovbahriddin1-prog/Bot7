from db import Database

async def build_daily_report(db: Database, days=1):
    groups, issues, questions, solved_count, tasks = await db.report_data(days)
    if not groups:
        return "Hozircha bot kuzatayotgan guruhlar yo‘q."

    title = "SO‘NGGI 7 KUN" if days == 7 else "BUGUNGI HOLAT"
    lines = [f"<b>{title}</b>", f"Ulangan guruhlar: {len(groups)}",
             f"Ochiq muammolar: {len(issues)} | Javobsiz savollar: {len(questions)}",
             f"Hal qilingan muammolar: {solved_count}", ""]

    lines.append("<b>Guruhlar kesimida:</b>")
    for g in groups:
        g_issues = [x for x in issues if x["chat_id"] == g["chat_id"]]
        g_questions = [x for x in questions if x["chat_id"] == g["chat_id"]]
        lines.append(f"• <b>{g['title']}</b>: {len(g_issues)} ochiq muammo, {len(g_questions)} javobsiz savol")

    if issues:
        lines += ["", "<b>Ochiq muammolar:</b>"]
        for x in issues[:15]:
            lines.append(f"• {x['group_title']}: {x['title']} — mas’ul: {x['responsible'] or 'aniqlanmagan'}")
    if questions:
        lines += ["", "<b>Javobsiz savollar:</b>"]
        for x in questions[:15]:
            lines.append(f"• {x['group_title']}: {x['question']} — so‘ragan: {x['asked_by'] or 'noma’lum'}")
    if tasks:
        lines += ["", "<b>Bajarilishi kutilayotgan vazifalar:</b>"]
        for x in tasks[:15]:
            lines.append(f"• {x['group_title']}: {x['title']} — {x['responsible'] or 'mas’ul aniqlanmagan'}")

    lines += ["", "<i>Eslatma: AI xulosalari guruh xabarlaridagi dalillarga asoslanadi. "
              "Noaniq mas’ul yoki yechim tasdiqlanmagan deb ko‘rsatilishi kerak.</i>"]
    return "\\n".join(lines)

"""Сценарный bot-flow без обращения к модели.

Детерминированные сценарии: главное меню, каталог услуг, FAQ,
обычная заявка и обратная связь. Работают даже без AI Studio API.
"""

from __future__ import annotations

from typing import Any

import storage

QUICK_MENU = ["Услуги", "FAQ", "Оставить заявку", "ИИ-консультант", "Обратная связь"]
BACK_LABEL = "Назад в меню"

SERVICES: list[dict[str, str]] = [
    {
        "id": "1",
        "name": "Керамическая посуда на заказ",
        "short": "Посуда на заказ",
        "price": "от 1 500 ₽",
        "desc": "Кружки, тарелки, миски, чайные пары и сервизы ручной лепки.",
    },
    {
        "id": "2",
        "name": "Декор и предметы интерьера",
        "short": "Декор для интерьера",
        "price": "от 3 000 ₽",
        "desc": "Вазы, кашпо, подсвечники, настенные панно под ваш размер и цвет.",
    },
    {
        "id": "3",
        "name": "Подарочные наборы и сервизы",
        "short": "Подарочные наборы",
        "price": "от 8 000 ₽",
        "desc": "Готовые и собранные под заказ наборы, возможна надпись.",
    },
    {
        "id": "4",
        "name": "Мастер-класс по лепке и гончарному кругу",
        "short": "Мастер-класс",
        "price": "от 2 500 ₽",
        "desc": "Индивидуально или в группе до 6 человек, материалы и обжиг включены.",
    },
    {
        "id": "5",
        "name": "Авторская мебель и крупные изделия",
        "short": "Авторская мебель",
        "price": "от 25 000 ₽",
        "desc": "Столики, полки, панно из керамики и дерева по индивидуальному проекту.",
    },
]

FAQ_CATEGORIES: list[dict[str, Any]] = [
    {
        "name": "Услуги",
        "items": [
            {
                "q": "Чем отличается посуда на заказ от готового декора?",
                "a": "Посуду лепим под ваши задачи (размер, цвет, назначение). Декор — это предметы интерьера: вазы, кашпо, панно, подсвечники.",
                "keywords": ["посуда", "декор", "отличие", "разница"],
            },
            {
                "q": "Можно ли заказать один предмет, а не набор?",
                "a": "Да, минимальный заказ — один предмет. Наборы и сервизы собираем по желанию.",
                "keywords": ["один предмет", "один", "набор", "минимум"],
            },
            {
                "q": "Что входит в мастер-класс?",
                "a": "Материалы, работа за гончарным кругом или ручная лепка, глазурь и обжиг. Готовое изделие забираете с собой.",
                "keywords": ["мастер-класс", "что входит", "обучение"],
            },
        ],
    },
    {
        "name": "Стоимость",
        "items": [
            {
                "q": "Сколько стоит посуда на заказ?",
                "a": "От 1 500 ₽ за предмет. Точная цена зависит от размера, сложности и глазури.",
                "keywords": ["стоит", "цена", "посуда", "сколько"],
            },
            {
                "q": "Что влияет на итоговую цену?",
                "a": "Размер изделия, сложность формы, тип глазури и срочность. Финальную стоимость называем после уточнения задачи.",
                "keywords": ["цена", "влияет", "стоимость", "итоговая"],
            },
            {
                "q": "Есть ли предоплата?",
                "a": "Да, предоплата 50% фиксирует заказ. Остаток — после готовности, до отправки или передачи.",
                "keywords": ["предоплата", "оплата", "аванс"],
            },
        ],
    },
    {
        "name": "Сроки и формат работы",
        "items": [
            {
                "q": "Сколько времени занимает заказ?",
                "a": "Посуда и декор — обычно 2–4 недели. Крупные изделия и мебель — от 4 недель. Точный срок называем при согласовании.",
                "keywords": ["срок", "сколько времени", "долго", "когда"],
            },
            {
                "q": "Как проходит работа над заказом?",
                "a": "Уточняем задачу → считаем стоимость → предоплата → изготовление → согласование фото → остаток и передача.",
                "keywords": ["этапы", "процесс", "как проходит", "формат"],
            },
            {
                "q": "Можно ли внести правки?",
                "a": "На этапе эскиза и формы — да. После обжига правки ограничены, поэтому форму согласовываем заранее.",
                "keywords": ["правки", "изменить", "исправить"],
            },
        ],
    },
    {
        "name": "Правила и контакты",
        "items": [
            {
                "q": "Есть ли гарантия?",
                "a": "Да, если изделие пришло с дефектом производства — заменим или вернём деньги в течение 14 дней.",
                "keywords": ["гарантия", "возврат", "брак", "дефект"],
            },
            {
                "q": "Как связаться с мастерской?",
                "a": "Через этот чат (оставьте заявку) или по почте hello@glina.example. Отвечаем в будни с 10:00 до 19:00.",
                "keywords": ["контакт", "связаться", "почта", "телефон"],
            },
            {
                "q": "Работаете ли вы по договору?",
                "a": "Для заказов от 25 000 ₽ и для юридических лиц оформляем договор.",
                "keywords": ["договор", "юрлицо", "юридическим"],
            },
        ],
    },
]

GREETING = (
    "Здравствуйте! Я чат-бот мастерской керамики, декора и авторской мебели «Глина».\n"
    "Выберите пункт меню или напишите свой вопрос."
)


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def menu_message() -> dict[str, Any]:
    return {"reply": GREETING, "quick_replies": QUICK_MENU}


def _services_text() -> str:
    lines = ["Наши услуги:", ""]
    for s in SERVICES:
        lines.append(f"{s['id']}. {s['name']} — {s['price']}")
        lines.append(f"   {s['desc']}")
    lines.append("")
    lines.append("Чтобы оставить заявку, выберите «Оставить заявку».")
    return "\n".join(lines)


def _faq_categories_text() -> str:
    lines = ["По какой теме хотите узнать?", ""]
    for i, cat in enumerate(FAQ_CATEGORIES, start=1):
        lines.append(f"{i}. {cat['name']}")
    return "\n".join(lines)


def _category_items(category: dict[str, Any]) -> str:
    lines = [f"Раздел «{category['name']}»:", ""]
    for item in category["items"]:
        lines.append(f"В: {item['q']}")
        lines.append(f"О: {item['a']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _find_service(text: str) -> dict[str, str] | None:
    t = _normalize(text)
    for s in SERVICES:
        variants = {
            s["id"],
            _normalize(s["short"]),
            _normalize(s["name"]),
            f"{s['id']}. {_normalize(s['short'])}",
            f"{s['id']}. {_normalize(s['name'])}",
        }
        if t in variants:
            return s
    return None


def _find_faq_answer(text: str) -> str | None:
    t = _normalize(text)
    for cat in FAQ_CATEGORIES:
        for item in cat["items"]:
            haystack = _normalize(item["q"] + " " + item["a"])
            if t and (t in haystack or any(k and _normalize(k) in t for k in item["keywords"])):
                return f"В: {item['q']}\nО: {item['a']}"
    return None


def _find_faq_category(text: str) -> dict[str, Any] | None:
    t = _normalize(text)
    for i, cat in enumerate(FAQ_CATEGORIES, start=1):
        if t in (_normalize(cat["name"]), str(i)):
            return cat
    return None


def start_lead(session: dict[str, Any]) -> dict[str, Any]:
    session["mode"] = "lead"
    session["lead_step"] = "service"
    session["lead_data"] = {}
    quick = [f"{s['id']}. {s['short']}" for s in SERVICES] + [BACK_LABEL]
    return {"reply": "Выберите услугу:\n\n" + _services_text(), "quick_replies": quick}


def _lead_service(session: dict[str, Any], text: str) -> dict[str, Any]:
    service = _find_service(text)
    if service is None:
        quick = [f"{s['id']}. {s['short']}" for s in SERVICES] + [BACK_LABEL]
        return {"reply": "Не нашёл такую услугу. Выберите из списка или напишите номер.", "quick_replies": quick}
    session["lead_data"]["service"] = service["name"]
    session["lead_step"] = "problem"
    return {
        "reply": f"Выбрано: {service['name']} ({service['price']}).\nКратко опишите задачу: что нужно сделать?",
        "quick_replies": [BACK_LABEL],
    }


def _lead_problem(session: dict[str, Any], text: str) -> dict[str, Any]:
    session["lead_data"]["problem_text"] = text
    session["lead_step"] = "contact"
    return {
        "reply": "Оставьте контакт для связи (имя и телефон, email или Telegram).",
        "quick_replies": [BACK_LABEL],
    }


def _lead_contact(session: dict[str, Any], text: str) -> dict[str, Any]:
    session["lead_data"]["contact"] = text
    data = session["lead_data"]
    storage.save_lead(
        session_id=session["id"],
        source="bot_flow",
        service=data.get("service"),
        problem_text=data.get("problem_text"),
        contact=data.get("contact"),
        agent_summary="Обычная заявка через сценарный bot-flow.",
        missing_info=None,
        status="new",
    )
    session["mode"] = "menu"
    session.pop("lead_step", None)
    session.pop("lead_data", None)
    return {
        "reply": "Спасибо! Заявка принята. Мы свяжемся с вами в ближайшее время.",
        "quick_replies": QUICK_MENU,
    }


def handle_lead(session: dict[str, Any], text: str) -> dict[str, Any]:
    step = session.get("lead_step", "service")
    if step == "service":
        return _lead_service(session, text)
    if step == "problem":
        return _lead_problem(session, text)
    return _lead_contact(session, text)


def start_feedback(session: dict[str, Any]) -> dict[str, Any]:
    session["mode"] = "feedback"
    return {"reply": "Напишите отзыв или пожелание одним сообщением — я сохраню его.", "quick_replies": [BACK_LABEL]}


def handle_feedback(session: dict[str, Any], text: str) -> dict[str, Any]:
    storage.save_feedback(session_id=session["id"], message_text=text)
    session["mode"] = "menu"
    return {"reply": "Спасибо! Обратная связь сохранена.", "quick_replies": QUICK_MENU}


def handle_services(session: dict[str, Any], text: str) -> dict[str, Any]:
    t = _normalize(text)
    if t in ("оставить заявку", "заявка", "заказать"):
        return start_lead(session)
    if t in ("faq", "вопросы", "частые вопросы"):
        return show_faq(session)
    session["mode"] = "menu"
    return menu_message()


def show_faq(session: dict[str, Any]) -> dict[str, Any]:
    session["mode"] = "faq"
    session.pop("faq_category", None)
    quick = [cat["name"] for cat in FAQ_CATEGORIES] + [BACK_LABEL]
    return {"reply": _faq_categories_text(), "quick_replies": quick}


def handle_faq(session: dict[str, Any], text: str) -> dict[str, Any]:
    category = _find_faq_category(text)
    if category is not None:
        session["faq_category"] = category["name"]
        return {
            "reply": _category_items(category),
            "quick_replies": ["Назад к разделам", BACK_LABEL],
        }

    t = _normalize(text)
    if t in ("назад к разделам", "разделы", "категории"):
        return show_faq(session)

    answer = _find_faq_answer(text)
    if answer is not None:
        return {"reply": answer, "quick_replies": ["Назад к разделам", BACK_LABEL]}

    quick = [cat["name"] for cat in FAQ_CATEGORIES] + [BACK_LABEL]
    return {
        "reply": "Не нашёл ответ на этот вопрос. Выберите раздел или напишите ключевое слово.",
        "quick_replies": quick,
    }


def handle_menu(session: dict[str, Any], text: str) -> dict[str, Any]:
    t = _normalize(text)
    if t == "":
        return menu_message()
    if t in ("услуги", "каталог", "прайс", "что вы делаете"):
        session["mode"] = "services"
        return {
            "reply": _services_text(),
            "quick_replies": ["Оставить заявку", "FAQ", BACK_LABEL],
        }
    if t in ("faq", "вопросы", "частые вопросы"):
        return show_faq(session)
    if t in ("оставить заявку", "заявка", "заказать"):
        return start_lead(session)
    if t in ("ии-консультант", "ии консультант", "консультант", "задать вопрос ии", "ии"):
        return {"switch_to": "ai"}
    if t in ("обратная связь", "отзыв", "feedback"):
        return start_feedback(session)
    return {"reply": "Не понял. Выберите пункт меню или напишите вопрос.", "quick_replies": QUICK_MENU}


def handle(session: dict[str, Any], text: str) -> dict[str, Any]:
    mode = session.get("mode", "menu")
    t = _normalize(text)

    if t in ("назад в меню", "меню", "главное меню", "назад"):
        session["mode"] = "menu"
        session.pop("lead_step", None)
        session.pop("lead_data", None)
        session.pop("faq_category", None)
        return menu_message()

    if mode == "services":
        return handle_services(session, text)
    if mode == "faq":
        return handle_faq(session, text)
    if mode == "lead":
        return handle_lead(session, text)
    if mode == "feedback":
        return handle_feedback(session, text)
    return handle_menu(session, text)

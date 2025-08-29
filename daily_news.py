import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai

openai_api_key = st.secrets.get("OPENAI_API_KEY", "")
app_password = st.secrets.get("NEWS_SUMMARY_PASSWORD", "")

# --- עיצוב: אליפסה מרכזית עם הכותרת בפנים + כל הכרטיסים למטה ---
st.markdown("""
    <style>
    header[data-testid="stHeader"] {background: none;}
    .css-18ni7ap.e8zbici2 {background: none !important; box-shadow: none !important;}
    .main-ellipse {
        direction: rtl;
        margin: 45px auto 27px auto;
        max-width: 600px;
        min-width: 270px;
        min-height: 76px;
        background: linear-gradient(92deg, #f5faff 0%, #f1f2fc 80%);
        border-radius: 65px;
        box-shadow: 0 2px 34px 0 #e5eafe94, 0 1.5px 10px 0 #e4e7f0;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .main-ellipse .ellipse-title {
        font-size: 2em;
        font-weight: bold;
        color: #2b2c37;
        padding: 17px 0px;
        width: 100%;
        text-align: center;
    }
    .main-card {
        direction: rtl;
        margin: 0 auto 32px auto;
        max-width: 530px;
        min-width: 340px;
        border-radius: 23px;
        box-shadow: 0 2px 24px 0 #b1b1c18a;
        background: #fff;
        padding: 32px 38px 29px 38px;
        text-align: center;
    }
    .main-card label, .main-card input, .main-card .stButton, .main-card select {
        font-size: 1.13em;
    }
    .main-card .stButton > button {
        font-size: 1.19em;
        font-weight: 600;
        border-radius: 14px !important;
        padding: 13px 0px;
        margin-top: 7px;
        margin-bottom: 20px;
        box-shadow: 0 1px 9px 0 #e2e7ef99;
    }
    </style>
""", unsafe_allow_html=True)

def get_google_news_rss(query="stock market", limit=12):
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "lxml-xml")
    news_items = []
    for idx, item in enumerate(soup.find_all('item')):
        title = item.title.text
        desc = item.description.text
        link = item.link.text
        news_items.append({
            'title': title,
            'desc': desc,
            'url': link,
            'idx': idx+1
        })
        if len(news_items) >= limit:
            break
    return news_items

def extract_keywords(news_items, openai_api_key, lang="he"):
    stories = ""
    for item in news_items:
        stories += f"{item['idx']}. {item['title']}\n{item['desc']}\n\n"
    if lang == "he":
        prompt = (
            "להלן כותרות ותקצירים של חדשות שוק ההון. "
            "החזר רשימה של 5-8 מילות מפתח או ביטויים מרכזיים (ללא סולמית), המייצגים את הנושאים המרכזיים של היום. "
            "הצג כל מילה או ביטוי מופרדים בפסיק אחד מהשני, בלי הסברים, רק המילים או הביטויים.\n\n"
            f"{stories}"
        )
    else:
        prompt = (
            "Below are today's main stock market news headlines and summaries. "
            "Return a list of 5-8 main keywords or key phrases (no #), summarizing the key topics of the day. "
            "Write them comma separated, no explanation, only the words or phrases.\n\n"
            f"{stories}"
        )
    client = openai.OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.4
    )
    keywords = [k.strip() for k in response.choices[0].message.content.split(',') if k.strip()]
    return keywords

def summarize_news(news_items, openai_api_key, lang="he", stock=None):
    stories = ""
    for item in news_items:
        stories += f"{item['idx']}. {item['title']}\n{item['desc']}\n\n"
    if stock:
        if lang == "he":
            prompt = (
                f"אתה עורך חדשות פיננסיות. להלן כותרות ותקצירים של חדשות מהיום על מניית {stock.upper()} (ממקורות שונים, ייתכן חפיפות). "
                "כתוב סיכום יומי ממוקד במניה בלבד ב־5 בולטים עיקריים, כאשר כל בולט הוא פסקה קצרה (שורה־שתיים) שמסבירה מה קרה סביב המניה, למה זה משמעותי ולמי זה נוגע. "
                "בסוף כל בולט, ציין בסוגריים את מספרי החדשות הרלוונטיים (למשל (1), (2,4)). "
                "הסיכום צריך להתייחס רק למידע שמופיע למטה, ולא לדבר על 'אפליקציות' או נושאים שאינם קשורים ישירות למניה זו.\n\n"
                f"{stories}"
            )
        else:
            prompt = (
                f"You are a financial news editor. Below are today's news headlines and summaries about the stock {stock.upper()} (from multiple sources, some may be similar). "
                "Write a focused daily summary in 5 main bullets about this company/ticker only. "
                "Each bullet should be a short paragraph about the facts, the context, and investor implications, using ONLY the information below. "
                "At the end of each bullet, in parentheses, list the news item numbers used. "
                "Do not summarize any news that is not directly related to this stock. "
                "Do not write about apps in general, only about the company/stock.\n\n"
                f"{stories}"
            )
    else:
        if lang == "he":
            prompt = (
                "אתה עורך חדשות פיננסיות. להלן כותרות ותקצירים של חדשות שוק ההון מהיום (ממקורות שונים, ייתכן חפיפות). "
                "כתוב סיכום יומי מפורט ב־5 בולטים עיקריים, כאשר כל בולט הוא פסקה קצרה (שורה־שתיים) שמסבירה מה קרה, למה זה משמעותי ולמי זה נוגע. "
                "בסוף כל בולט, ציין בסוגריים את מספרי החדשות הרלוונטיים (למשל (1), (2,4)). "
                "הסיכום צריך לאפשר להבין הכל בלי לקרוא את הכתבות עצמן.\n\n"
                f"{stories}"
            )
        else:
            prompt = (
                "You are a financial news editor. Below are today's major stock market news headlines and summaries (from multiple sources, some may be similar). "
                "Write a concise daily market summary in 5 main bullets. "
                "Each bullet should be a short paragraph that covers the key fact, the market context, and what it means for investors, using ONLY the information below. "
                "At the end of each bullet, in parentheses, list the news item numbers you used (e.g., (1), (3,6)). "
                "This summary should give the reader a complete and focused understanding of today's market events without needing to read the articles themselves.\n\n"
                f"{stories}"
            )
    client = openai.OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.5
    )
    return response.choices[0].message.content.strip()

def render_bullets_with_buttons(summary_text, news_items, lang="he"):
    import re
    idx_to_url = {item['idx']: item['url'] for item in news_items}
    lines = [line.strip() for line in summary_text.split('\n') if line.strip()]
    label = "לכתבה" if lang == "he" else "Article"
    for i, line in enumerate(lines, 1):
        m = re.search(r'\(([\d, ]+)\)', line)
        if m:
            nums = [int(x.strip()) for x in m.group(1).split(',')]
            bullet_text = line.replace(m.group(0), "")
            st.markdown(
                f"""<div style="direction:rtl;text-align:right;font-size:1.15em;margin-bottom:18px;
                border-radius:10px;background-color:#F9F9FB;padding:13px 18px;">
                {bullet_text}
                <div style="margin-top:7px;">""" +
                "".join([
                    f"""<a href="{idx_to_url[n]}" target="_blank">
                        <button style='margin-left:7px;margin-bottom:2px;
                        background:#2557a7;color:#fff;padding:3.2px 15px;border:none;
                        border-radius:12px;font-size:0.92em;cursor:pointer;'>
                        {label} {n}</button></a>""" for n in nums if n in idx_to_url
                ]) +
                """</div></div>""", unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""<div style="direction:rtl;text-align:right;font-size:1.15em;margin-bottom:18px;
                border-radius:10px;background-color:#F9F9FB;padding:13px 18px;">{line}</div>""",
                unsafe_allow_html=True
            )

st.set_page_config(page_title="סיכום חדשות שוק ההון", page_icon="💹", layout="centered")
# **שורת ה-title הוסרה כאן**

# ---- אליפסה עם כותרת בפנים ----
st.markdown(
    """
    <div class='main-ellipse'>
        <span class='ellipse-title'>
            <span style='font-size:1.13em; margin-left:10px;'>💹</span>
            בחר אפשרות לסיכום:
        </span>
    </div>
    """, unsafe_allow_html=True
)

# ---- כרטיס עיצוב מרכזי ----
with st.container():
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    general_news = st.button("סיכום שוק כללי", use_container_width=True)
    st.markdown("<hr style='border:none;border-top:1.5px solid #e4e7f0;margin:15px 0 18px 0;'>", unsafe_allow_html=True)
    stock_name = st.text_input("שם מניה (באנגלית או סימול):", value="", key="stock_input", placeholder="למשל: NVDA")
    stock_news = st.button("סיכום עבור מניה זו", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if not openai_api_key:
    st.error("לא נמצא מפתח OpenAI. יש להכניס אותו ל-secrets.toml תחת OPENAI_API_KEY")
    st.stop()

user_pass = st.text_input("הכנס סיסמה לשימוש במערכת:", type="password")
if not user_pass:
    st.info("הכנס סיסמה בשביל להמשיך.")
    st.stop()
if user_pass != app_password:
    st.error("סיסמה שגויה.")
    st.stop()

lang = st.radio("בחר שפת סיכום:", ["עברית", "English"], horizontal=True)
lang_code = "he" if lang == "עברית" else "en"

if general_news or stock_news:
    if general_news:
        query = "stock market"
        title_for_summary = "סיכום יומי"
        stock_context = None
    else:
        query = f"{stock_name.strip()} stock" if stock_name.strip() else "stock market"
        title_for_summary = f"סיכום חדשות עבור {stock_name.upper()}" if stock_name.strip() else "סיכום יומי"
        stock_context = stock_name.strip() if stock_name.strip() else None

    with st.spinner("טוען חדשות מ-Google News..."):
        news = get_google_news_rss(query=query, limit=12)
    with st.spinner("מזהה מילות מפתח עיקריות..."):
        keywords = extract_keywords(news, openai_api_key, lang=lang_code)
    if keywords:
        st.markdown(
            "<div style='direction:rtl;text-align:right; margin-bottom:8px; margin-top:8px;'>"
            + " ".join(
                [f"<span style='display:inline-block; margin-left:6px; background:#f0f4fc; color:#2251a2; font-weight:bold; padding:4px 15px; border-radius:13px; font-size:1.05em;'>{k}</span>"
                 for k in keywords]
            )
            + "</div>",
            unsafe_allow_html=True
        )
    with st.spinner("מסכם עם GPT..."):
        summary = summarize_news(news, openai_api_key, lang=lang_code, stock=stock_context)
    st.subheader(title_for_summary)
    render_bullets_with_buttons(summary, news, lang=lang_code)
    with st.expander("הצג את רשימת כל הכותרות (לא חובה)", expanded=False):
        for n in news:
            desc_to_show = n["desc"].strip()
            show_desc = desc_to_show and desc_to_show != n["title"]
            st.markdown(
                f'<div style="direction:rtl;text-align:right; margin-bottom:10px;">'
                f'<b>{n["idx"]}. <a href="{n["url"]}" target="_blank">{n["title"]}</a></b>'
                + (f'<br><span style="color: #555;">{desc_to_show}</span>' if show_desc else '') +
                f'</div>',
                unsafe_allow_html=True
            )
else:
    st.info("לחץ על אחד מהכפתורים כדי להציג את הסיכום היומי.")

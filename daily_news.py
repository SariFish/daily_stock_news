import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai

openai_api_key = st.secrets.get("OPENAI_API_KEY", "")
app_password = st.secrets.get("NEWS_SUMMARY_PASSWORD", "")

st.set_page_config(page_title="סיכום חדשות שוק ההון", page_icon="💹", layout="centered")

st.markdown("""
    <style>
    header[data-testid="stHeader"] {background: none;}
    section.main {padding-top:32px;}
    /* כותרת עמוד */
    .headline-main {
        font-size:2.7em; font-weight:800; text-align:center; color:#242628;
        letter-spacing:-1px; margin-bottom:22px; margin-top:10px;
    }
    /* קופסה לסיסמה */
    .pw-box {
        max-width:340px; margin:48px auto 25px auto; background:#f6f8fa;
        border-radius:19px; box-shadow:0 2px 15px #d6deeb30;
        padding:33px 35px 20px 35px; display:flex; flex-direction:column; align-items:center;
    }
    /* שלב הבחירה */
    .select-row {
        display:flex; flex-direction:row; gap:22px; justify-content:center; margin-bottom:23px;
    }
    @media (max-width:650px) {
      .select-row {flex-direction:column; gap:14px;}
    }
    .option-btn {
        background: #f4f7fb; color:#2a3444; font-size:1.19em; font-weight:600;
        padding:20px 0px; border:none; border-radius:17px; width:260px; box-shadow:0 1px 8px #e8eefa25;
        transition: box-shadow 0.13s, background 0.13s;
        cursor:pointer; margin-bottom:0px;
    }
    .option-btn.active, .option-btn:hover {
        background: #dde8fa;
        box-shadow: 0 1.5px 16px #b7cdfb35;
        color:#184d96;
        outline: 2.5px solid #b2d5ff;
    }
    /* שדה טיקר */
    .ticker-wrap {
        margin:0 auto 17px auto; max-width:350px; display:flex; flex-direction:column; align-items:center;
    }
    .ticker-label {margin-bottom:7px; font-weight:500; color:#252b38; font-size:1.1em;}
    .ticker-inp input {
        background:#f4f7fb !important; border-radius:14px !important;
        font-size:1.2em !important; text-align:center;
        font-weight:500;
    }
    /* language selector */
    .lang-row {display:flex; gap:18px; align-items:center; justify-content:center; margin:10px 0 20px 0;}
    .lang-radio label {font-size:1.09em !important;}
    /* פידבק */
    .small-note {
        color:#467ae2; background:#f0f7ff; border-radius:13px; font-size:1.08em;
        margin:24px auto 0 auto; padding:13px 11px; text-align:center; max-width:400px;
    }
    /* פלט הסיכום */
    .result-block {
        margin: 35px auto 24px auto; max-width:590px; background:#fcfdfe;
        border-radius:23px; box-shadow:0 2px 13px #dce4ec33;
        padding: 30px 30px 20px 30px; direction:rtl;
    }
    .result-block h3 {margin-top:0;}
    </style>
""", unsafe_allow_html=True)

# -- 1. סיסמה -- #
if "passed_pw" not in st.session_state:
    st.session_state["passed_pw"] = False

if not st.session_state["passed_pw"]:
    st.markdown("<div class='headline-main'>סיכום יומי של חדשות שוק ההון</div>", unsafe_allow_html=True)
    with st.form("pw-form"):
        st.markdown("<div class='pw-box'><b>הכנס סיסמה לשימוש במערכת:</b>", unsafe_allow_html=True)
        pw = st.text_input("", type="password", key="pwbox", label_visibility="collapsed")
        submitted = st.form_submit_button("המשך")
        st.markdown("</div>", unsafe_allow_html=True)
        if submitted:
            if not pw:
                st.warning("יש למלא סיסמה")
                st.stop()
            if pw == app_password:
                st.session_state["passed_pw"] = True
            else:
                st.error("סיסמה שגויה.")
                st.stop()
        else:
            st.stop()

# -- 2. כותרת מרכזית -- #
st.markdown("<div class='headline-main'>סיכום יומי של חדשות שוק ההון</div>", unsafe_allow_html=True)

# -- 3. בחירת אפשרות סיכום -- #
if "option" not in st.session_state:
    st.session_state["option"] = None

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("סיכום שוק כללי", key="opt_general", help="סיכום יומי על שוק ההון כולו", use_container_width=True):
        st.session_state["option"] = "general"
with col2:
    if st.button("סיכום עבור מניה", key="opt_stock", help="סיכום ממוקד עבור מניה", use_container_width=True):
        st.session_state["option"] = "stock"

# -- 4. אם בחר מניה, נפתח שדה מניה -- #
stock_name = ""
if st.session_state["option"] == "stock":
    st.markdown("<div class='ticker-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='ticker-label'>שם מניה (סימול באנגלית):</div>", unsafe_allow_html=True)
    stock_name = st.text_input("", value="", key="stock_input", placeholder="למשל: NVDA", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    stock_news = st.button("סיכום עבור מניה זו", key="do_stock", use_container_width=True)
else:
    stock_news = False

# -- 5. אפשרות לשפה -- #
st.markdown("<div class='lang-row'>בחר שפת סיכום:", unsafe_allow_html=True)
lang = st.radio("", ["עברית", "English"], horizontal=True, key="lang_radio")
st.markdown("</div>", unsafe_allow_html=True)
lang_code = "he" if lang == "עברית" else "en"

# -- 6. הלוגיקה -- #
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

# == Logic Execution ==
trigger = False
if st.session_state["option"] == "general":
    if st.button("הצג סיכום יומי", key="show_general", use_container_width=True):
        trigger = True
        query = "stock market"
        stock_context = None
elif st.session_state["option"] == "stock" and stock_name.strip():
    if stock_news:
        trigger = True
        query = f"{stock_name.strip()} stock"
        stock_context = stock_name.strip()
    else:
        st.stop()
else:
    st.markdown("<div class='small-note'>בחר/י אפשרות לסיכום יומי והשלם/י את הפרטים</div>", unsafe_allow_html=True)
    st.stop()

if trigger:
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
    st.markdown("<div class='result-block'>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-bottom:12px;'>{'סיכום יומי' if not stock_context else f'סיכום עבור {stock_context.upper()}'}</h3>", unsafe_allow_html=True)
    render_bullets_with_buttons(summary, news, lang=lang_code)
    st.markdown("</div>", unsafe_allow_html=True)
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

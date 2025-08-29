import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai

openai_api_key = st.secrets.get("OPENAI_API_KEY", "")
app_password = st.secrets.get("NEWS_SUMMARY_PASSWORD", "")

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

def summarize_news(news_items, openai_api_key, lang="he"):
    stories = ""
    for item in news_items:
        stories += f"{item['idx']}. {item['title']}\n{item['desc']}\n\n"
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

def render_bullets_with_links(summary_text, news_items):
    import re
    idx_to_url = {item['idx']: item['url'] for item in news_items}
    lines = summary_text.splitlines()
    new_bullets = []
    for line in lines:
        m = re.search(r'\(([\d, ]+)\)', line)
        if m:
            nums = [int(x.strip()) for x in m.group(1).split(',')]
            links = []
            for n in nums:
                url = idx_to_url.get(n)
                if url:
                    links.append(f"[לכתבה {n}]({url})")
            links_str = " ".join(links)
            bullet_text = line.replace(m.group(0), "")
            new_bullets.append(
                f'<li style="direction:rtl;text-align:right;font-size:1.1em;margin-bottom:12px;">{bullet_text} <span style="font-size:0.9em;">{links_str}</span></li>'
            )
        else:
            new_bullets.append(
                f'<li style="direction:rtl;text-align:right;font-size:1.1em;margin-bottom:12px;">{line}</li>'
            )
    html = "<ul style='padding-right:18px;'>" + "\n".join(new_bullets) + "</ul>"
    st.markdown(html, unsafe_allow_html=True)

st.set_page_config(page_title="סיכום חדשות שוק ההון", page_icon="💹", layout="centered")
st.title("💹 סיכום חדשות שוק ההון - Google News")

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

if st.button("עדכן והצג חדשות אחרונות"):
    with st.spinner("טוען חדשות מ-Google News..."):
        news = get_google_news_rss(query="stock market", limit=12)
    st.subheader("החדשות העדכניות")
    for n in news:
        desc_to_show = n["desc"].strip()
        show_desc = desc_to_show and desc_to_show != n["title"]
        st.markdown(
            f'<div style="direction:rtl;text-align:right; margin-bottom:14px;">'
            f'<b>{n["idx"]}. <a href="{n["url"]}" target="_blank">{n["title"]}</a></b>'
            + (f'<br><span style="color: #555;">{desc_to_show}</span>' if show_desc else '') +
            f'</div>',
            unsafe_allow_html=True
        )
    with st.spinner("מסכם עם GPT..."):
        summary = summarize_news(news, openai_api_key, lang=lang_code)
    st.subheader("סיכום GPT")
    render_bullets_with_links(summary, news)
else:
    st.info("לחץ על הכפתור כדי להציג את החדשות האחרונות והסיכום.")

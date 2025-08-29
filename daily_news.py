import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai

openai_api_key = st.secrets.get("OPENAI_API_KEY", "")
app_password = st.secrets.get("NEWS_SUMMARY_PASSWORD", "")

def get_yahoo_finance_news(limit=12):
    url = "https://finance.yahoo.com/news/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    news_items = []
    seen = set()
    for idx, item in enumerate(soup.find_all('li', {'class': 'js-stream-content'})):
        title_tag = item.find('h3')
        desc_tag = item.find('p')
        link_tag = item.find('a', href=True)
        if title_tag and link_tag:
            title = title_tag.get_text(strip=True)
            url = "https://finance.yahoo.com" + link_tag['href']
            if title in seen:
                continue
            seen.add(title)
            desc = desc_tag.get_text(strip=True) if desc_tag else ""
            news_items.append({
                'title': title,
                'desc': desc,
                'url': url,
                'idx': idx+1 # סידור לזיהוי בולטים
            })
            if len(news_items) >= limit:
                break
    return news_items

def summarize_news(news_items, openai_api_key):
    stories = ""
    for item in news_items:
        stories += f"{item['idx']}. {item['title']}\n{item['desc']}\n\n"
    prompt = (
        "Here are stock market news items from Yahoo Finance today. "
        "Each item has a headline and summary. "
        "Summarize in up to 5 concise bullet points (in English), ONLY using the provided news items, without adding news or context that doesn't appear here. "
        "For each bullet, mention the number of the related news item in parentheses. "
        "Example: (3) or (1,4) if more than one. "
        "Do NOT add news about Israel or any other topic that is not shown in the news below.\n\n"
        f"{stories}"
    )
    client = openai.OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=450,
        temperature=0.5
    )
    return response.choices[0].message.content.strip()

def render_bullets_with_links(summary_text, news_items):
    idx_to_url = {item['idx']: item['url'] for item in news_items}
    lines = summary_text.splitlines()
    new_bullets = []
    for line in lines:
        # מוצא מספר בסוף הבולט (או בפנים) - דוג' (3), (2,4)
        import re
        m = re.search(r'\(([\d, ]+)\)', line)
        if m:
            nums = [int(x.strip()) for x in m.group(1).split(',')]
            # מוסיף קישורים (אם קיימים)
            links = []
            for n in nums:
                url = idx_to_url.get(n)
                if url:
                    links.append(f"[לכתבה {n}]({url})")
            links_str = " ".join(links)
            # שם הבולט בימין (rtl) ומוסיף קישור
            bullet_text = line.replace(m.group(0), "")  # מוריד את ה-(X)
            new_bullets.append(
                f'<li style="direction:rtl;text-align:right;font-size:1.1em;">{bullet_text} <span style="font-size:0.9em;">{links_str}</span></li>'
            )
        else:
            # בולט בלי מספרים
            new_bullets.append(
                f'<li style="direction:rtl;text-align:right;font-size:1.1em;">{line}</li>'
            )
    html = "<ul>" + "\n".join(new_bullets) + "</ul>"
    st.markdown(html, unsafe_allow_html=True)

# -- אפליקציית סטרימליט --
st.set_page_config(page_title="סיכום חדשות שוק ההון", page_icon="💹", layout="centered")
st.title("💹 סיכום חדשות שוק ההון - Yahoo Finance")

if not openai_api_key:
    st.error("לא נמצא מפתח OpenAI. יש להכניס אותו ל-secrets.toml תחת OPENAI_API_KEY")
    st.stop()

# -- דרישת סיסמה --
user_pass = st.text_input("הכנס סיסמה לשימוש במערכת:", type="password")
if not user_pass:
    st.info("הכנס סיסמה בשביל להמשיך.")
    st.stop()
if user_pass != app_password:
    st.error("סיסמה שגויה.")
    st.stop()

if st.button("עדכן והצג חדשות אחרונות"):
    with st.spinner("טוען חדשות מ-Yahoo..."):
        news = get_yahoo_finance_news(limit=12)
    st.subheader("החדשות העדכניות")
    for n in news:
        st.markdown(
            f'<div style="direction:rtl;text-align:right;">'
            f'<b>{n["idx"]}. <a href="{n["url"]}" target="_blank">{n["title"]}</a></b><br>'
            f'{n["desc"]}'
            f'</div>',
            unsafe_allow_html=True
        )
    with st.spinner("מסכם עם GPT..."):
        summary = summarize_news(news, openai_api_key)
    st.subheader("סיכום GPT")
    render_bullets_with_links(summary, news)
else:
    st.info("לחץ על הכפתור כדי להציג את החדשות האחרונות והסיכום.")

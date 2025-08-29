import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai

# ===========================
# קבלת מפתח OpenAI מהסודות
# ===========================
openai_api_key = st.secrets.get("OPENAI_API_KEY", "")

# ===========================
# פונקציה: גרידת חדשות
# ===========================
def get_yahoo_finance_news(limit=12):
    url = "https://finance.yahoo.com/news/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    news_items = []
    seen = set()
    for item in soup.find_all('li', {'class': 'js-stream-content'}):
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
                'url': url
            })
            if len(news_items) >= limit:
                break
    return news_items

# ===========================
# פונקציה: סיכום עם GPT
# ===========================
def summarize_news(news_items, openai_api_key):
    stories = ""
    for i, item in enumerate(news_items, 1):
        stories += f"{i}. {item['title']}\n{item['desc']}\n\n"
    prompt = (
        f"להלן חדשות שוק ההון מהיום, כל פריט כולל כותרת ותקציר.\n"
        f"סכם לי ב-5 בולטים קצרים בעברית את עיקרי החדשות החשובות ביותר עבור משקיע ישראלי ממוצע:\n"
        f"{stories}"
    )
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        api_key=openai_api_key,
        max_tokens=400,
        temperature=0.5
    )
    return response.choices[0].message.content.strip()

# ===========================
# Streamlit UI
# ===========================
st.set_page_config(page_title="סיכום חדשות שוק ההון", page_icon="💹", layout="centered")
st.title("💹 סיכום חדשות שוק ההון - Yahoo Finance")

if not openai_api_key:
    st.error("לא נמצא מפתח OpenAI. יש להכניס אותו ל-secrets.toml")
    st.stop()

if st.button("עדכן והצג חדשות אחרונות"):
    with st.spinner("טוען חדשות מ-Yahoo..."):
        news = get_yahoo_finance_news(limit=12)
    st.subheader("החדשות העדכניות")
    for n in news:
        st.markdown(
            f"**[{n['title']}]({n['url']})**  \n"
            f"{n['desc']}"
        )
    with st.spinner("מסכם עם GPT..."):
        summary = summarize_news(news, openai_api_key)
    st.subheader("סיכום GPT")
    st.markdown(summary)
else:
    st.info("לחץ על הכפתור כדי להציג את החדשות האחרונות והסיכום.")


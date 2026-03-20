import feedparser
import anthropic
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import os

# ── 1. FETCH NEWS FROM RSS FEEDS ──────────────────────────
RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",           # BBC World
    "https://www.thehindu.com/feeder/default.rss",      # The Hindu
    "https://feeds.feedburner.com/ndtvnews-top-stories", # NDTV
    "https://economictimes.indiatimes.com/rssfeedsdefault.cms", # ET
    "https://techcrunch.com/feed/",                     # TechCrunch
]

def fetch_headlines(max_per_feed=4):
    headlines = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        source = feed.feed.get("title", "Unknown")
        for entry in feed.entries[:max_per_feed]:
            headlines.append({
                "title": entry.title,
                "link": entry.link,
                "source": source
            })
    return headlines

# ── 2. SUMMARISE WITH CLAUDE API ──────────────────────────
def summarise_headlines(headlines):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    titles = "\n".join([f"- {h['title']} ({h['source']})" 
                        for h in headlines])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""You are a news editor. Given these headlines, 
write a concise morning briefing. Group by topic (World, India, Tech, etc.).
For each group write 2-3 bullet points, each one sentence.
Be factual and neutral. Headlines:\n{titles}"""
        }]
    )
    return message.content[0].text

# ── 3. BUILD HTML EMAIL ───────────────────────────────────
def build_email(summary):
    date = datetime.now().strftime("%A, %d %B %Y")
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;
    margin:auto;padding:20px;color:#333;">
      <h2 style="color:#1a1a1a;border-bottom:2px solid #eee;
      padding-bottom:10px;">Morning News Digest — {date}</h2>
      <div style="line-height:1.8;font-size:15px;">
        {summary.replace(chr(10), '<br>')}
      </div>
      <p style="color:#999;font-size:12px;margin-top:30px;">
        Powered by Claude AI · Delivered at 7:00 AM IST
      </p>
    </body></html>"""
    return html

# ── 4. SEND VIA GMAIL ─────────────────────────────────────
def send_email(html_body, recipients):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your Morning News Digest — {datetime.now().strftime('%d %b')}"
    msg["From"] = os.environ["GMAIL_USER"]
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["GMAIL_USER"], 
                     os.environ["GMAIL_APP_PASSWORD"])
        server.sendmail(os.environ["GMAIL_USER"], recipients, 
                        msg.as_string())
    print(f"Digest sent to {len(recipients)} recipient(s)!")

# ── 5. MAIN ───────────────────────────────────────────────
if __name__ == "__main__":
    RECIPIENTS = ["ayushnandy1802@gmail.com", "ashispoddar99@gmail.com"]  # add any emails
    print("Fetching headlines...")
    headlines = fetch_headlines()
    print(f"Got {len(headlines)} headlines. Summarising with Claude...")
    summary = summarise_headlines(headlines)
    html = build_email(summary)
    send_email(html, RECIPIENTS)

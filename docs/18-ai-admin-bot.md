# 18 — AI Admin Bot (Telegram)

Pastorn pratar med kyrkan via Telegram. Boten lyssnar, förstår,
bekräftar och agerar. Amharic, svenska och engelska.

## Varför Telegram-bot istället för admin-web?

| | Admin-web (formulär) | Telegram-bot |
|---|---|---|
| Pastorn behöver | Dator, webbläsare, URL, login | Telegram (redan på telefonen) |
| Tid att publicera en aktivitet | 3-5 minuter | 30 sekunder |
| Språk | Svenska UI | Amharic röst eller text |
| Tillgänglighet | Måste vara vid datorn | Var som helst, när som helst |
| Tekniknivå krävd | Kan använda ett formulär | Kan prata |

Admin-web finns kvar för komplex admin (bidrag, KPI, GDPR).
Telegram-boten är för **dagliga uppgifter**: publicera, kolla stats,
översätta.

## Flöde: pastor publicerar gudstjänst via röst

```
Pastor (röstmeddelande på amharic):
  "ሰንበት ቅዳሴ 11:00 ላይ ጨምር"
  (Lägg till gudstjänst söndag kl 11)

  ↓ Telegram skickar voice → n8n webhook

Step 1: Whisper transkriberar (am-ET)
  → "ሰንበት ቅዳሴ 11:00 ላይ ጨምር" (med ~30% fel möjligt)

Step 2: Claude korrigerar + klassificerar
  → {
      "intent": "add_activity",
      "corrected_text": "ሰንበት ቅዳሴ 11:00 ላይ ጨምር",
      "parameters": {
        "title_am": "ቅዳሴ",
        "title_sv": "Gudstjänst",
        "date": "2025-06-08",
        "time": "11:00"
      },
      "confidence": 0.92
    }

Step 3: Bot bekräftar
  → "ይህን ልጨምር: ቅዳሴ 2025-06-08 11:00?
     [✅ አዎ] [❌ አይ] [✏️ አስተካክል]"

Step 4: Pastor trycker ✅
  → Bot: "ተፈጽሟል ✅ ቅዳሴ ተጨምሯል"
  → content.json uppdateras
  → Telegram-kanalen notifieras
  → kyrka-portal.pages.dev visar den nya aktiviteten
```

## Stödda kommandon

| Avsikt | Amharic | Svenska |
|---|---|---|
| Lägg till aktivitet | "ሰንበት ቅዳሴ ጨምር" | "Lägg till gudstjänst" |
| Publicera meddelande | "ማስታወቂያ: ነገ ጥምቀት" | "Nytt meddelande: dop imorgon" |
| Kolla medlemsantal | "ስንት አባላት አሉን?" | "Hur många medlemmar?" |
| Kolla bidrag | "ምን ድጋፎች ማመልከት እንችላለን?" | "Vilka bidrag kan vi söka?" |
| Generera rapport | "የወሩን ሪፖርት አዘጋጅ" | "Generera månadsrapport" |
| Översätt | "ወደ ስዊድንኛ ተርጉም: ..." | "Översätt till amharic: ..." |

## Säkerhet

- Bara auktoriserade Telegram-användare (admin user IDs i n8n)
- Boten kan ALDRIG visa persondata (namn, personnummer)
- Boten kan visa aggregat (total members, activity counts)
- Human-in-the-loop: ALLTID bekräftelse innan publicering
- Inga PII-fält i blocked_fields-listan

## Whisper + Amharic: begränsningar

Whispers WER (Word Error Rate) för amharic är ~30-40%. Det
kompenseras av:

1. Claude som andra steg — korrigerar grammatik + kyrktermer
2. Bekräftelse innan aktion — pastorn ser vad boten tolkade
3. Kyrkoterminologi i system-prompten — Claude vet att ቅዳሴ=liturgi

Om pastorn upplever att röst inte fungerar bra: text fungerar
perfekt. Claude förstår amharic text med ~99% noggrannhet.

## Setup

1. Skapa bot via @BotFather i Telegram
2. Sätt `TELEGRAM_BOT_TOKEN` i Secret Manager
3. Importera workflow `telegram_admin_bot.json` i n8n
4. Lägg till pastorns Telegram user ID i allowed-listan
5. Konfigurera webhook: `https://n8n.kyrka.se/webhooks/telegram-bot`

Tid: ~15 minuter.

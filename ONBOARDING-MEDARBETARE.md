# Medarbetare & Administratörer — Kom igång

Välkommen! Den här guiden är skriven för dig som arbetar i kyrkan (t.ex. som pastor, redaktör eller styrelsemedlem) och ska använda kyrk-portalen i ditt dagliga arbete.

Portalen är byggd för att vara **extremt enkel att använda**, kräva **minimalt med underhåll** och **skydda medlemmarnas integritet** till 100 %.

---

## 1. Dina inloggningsuppgifter (Roller)

Du loggar in säkert via **Zitadel Cloud** med din e-postadress. Beroende på vad du arbetar med i kyrkan har du en av följande fyra roller:

*   **Pastor**: Kan godkänna nya medlemmar och utfärda kyrkliga certifikat (dopbevis, vigselbevis etc.).
*   **Redaktör (Editor)**: Kan lägga till aktiviteter i kalendern och redigera texter på hemsidan (svenska och amhariska).
*   **Granskare (Viewer)**: Kan titta på statistik (t.ex. hur många som besökt en aktivitet) och läsa ekonomiska rapporter, men inte ändra något.
*   **Admin (IT/Styrelse)**: Full behörighet till hela systemet, inklusive att bjuda in nya medarbetare och hantera tekniska inställningar.

---

## 2. Vanliga arbetsuppgifter

### Godkänna en ny medlem
När någon fyller i formuläret "Bli medlem" på hemsidan hamnar de under fliken **Intake** (Väntande medlemmar).
1.  Gå till **Intake** i menyn.
2.  Klicka på personen för att se deras uppgifter.
3.  Kontrollera att namnet är korrekt stavat.
4.  Klicka på **Godkänn** (Approve) eller **Avvisa** (Reject).
5.  *När du klickar på godkänn krypteras personnumret automatiskt i bakgrunden så att obehöriga aldrig kan läsa det.*

### Utfärda ett certifikat (t.ex. dopbevis eller vigselbevis)
Denna funktion kräver att du är inloggad som **Pastor** eller **Admin**.
1.  Gå till **Utfärda certifikat**.
2.  Välj certifikattyp (t.ex. *Baptism* eller *Marriage*).
3.  Fyll i medlemmens uppgifter och datum.
4.  Klicka på **Generera**. Systemet skapar då ett officiellt certifikat med ett unikt verifieringsnummer.

### Ändra text på hemsidan (Content Editor)
Som **Redaktör** kan du ändra texter och meddelanden.
1.  Gå till **Innehåll** (Content-editor).
2.  Skriv in din nya text på svenska.
3.  Klicka på **Översätt**. En inbyggd AI-assistent hjälper dig att automatiskt översätta texten till amhariska.
4.  **VIKTIGT (Mänsklig kontroll)**: AI-översättningen sparas i ett utkast. Du måste läsa igenom den amhariska texten och klicka på **Godkänn** innan den publiceras på den publika hemsidan. Detta förhindrar felöversättningar.

---

## 3. GDPR och Integritet (Regulatoriska krav)

Som kyrka hanterar vi känsliga personuppgifter (medlemskap i ett trossamfund är en känslig uppgift enligt lag). Systemet är byggt för att följa **GDPR** till punkt och pricka:

1.  **Krypterade personnummer**: Alla personnummer krypteras med en egen krypteringsnyckel (Google Cloud KMS) innan de sparas i databasen. Ingen medarbetare, inte ens systemadministratören, kan läsa personnumren i klartext i databasen.
2.  **Ingen spårning (Cookies)**: Hemsidan använder inga spårningskakor, ingen marknadsföringsspårning och skickar ingen data till Google Analytics. Två funktionella kakor sparar besökarens egna val (språk och vald församling) så att rätt innehåll visas — de spårar inte och delas inte med tredje part.
3.  **GDPR-register**: Systemet skapar automatiskt det register över personuppgiftsbehandlingar (Artikel 30) som Integritetsskyddsmyndigheten (IMY) kräver av oss.

---

## 4. EU AI Act och Bidragshantering (Governance)

När vi söker statsbidrag (t.ex. från MUCF eller Sveriges kristna råd) ställs det höga krav på digital säkerhet och etisk teknik. Dessutom påverkas vi av **EU AI Act** (EU:s AI-förordning) eftersom vi använder AI (Anthropic/Claude) för översättningar och ansökningsutkast.

Här är hur vi följer kraven för att säkra våra bidrag och klara revisioner:

### 1. Inga personuppgifter till AI (Dataskydd)
Vår AI-assistent får **aldrig** se personnamn, personnummer, adresser, telefonnummer eller e-postadresser. 
*   *Teknisk spärr*: Systemet har en inbyggd säkerhetsspärr (Sanitizer) som automatiskt blockerar och raderar alla personuppgifter *innan* en förfrågan skickas till AI-modellen. 
*   *Revision*: Detta visar för bidragsgivare och revisorer att vi upprätthåller strikt sekretess enligt dataskyddslagen.

### 2. Människan i loopen (EU AI Act Compliance)
Enligt EU AI Act får AI inte fatta självständiga beslut som påverkar människor.
*   *Vår lösning*: Alla AI-genererade texter (översättningar, utkast till bidragsansökningar) hamnar alltid i ett "utkastläge" som en mänsklig medarbetare (redaktör eller administratör) aktivt måste granska och godkänna manuellt.

### 3. Transparens
Om vi publicerar en text som är helt eller delvis genererad av AI på vår hemsida eller i en ansökan, bör vi vara transparenta med detta om bidragsgivaren kräver det. Systemet loggar internt vilka texter som har översatts med hjälp av AI.

---

## 5. Support och felsökning

Om inloggningen eller hemsidan inte fungerar:
1.  Kontrollera att du använder **http://localhost:8080/login** för lokala tester, eller den officiella adressen för drift.
2.  Om du får meddelandet "not authenticated" betyder det att din session har gått ut. Gå till login-sidan och logga in igen.
3.  Kontakta Daniel (eller din IT-ansvarige) om du behöver återställa ditt lösenord eller bjuda in en ny medarbetare i Zitadel.

# DigiTech-Spiner

DigiTech-Spiner je moderní GUI aplikace postavená na frameworku **PySide6** pro interaktivní vizualizaci, detekci a editaci vertebrálních (páteřových) bodů na X-ray (RTG) snímcích.
Projekt obsahuje pokročilé nástroje pro manipulaci s body postavenými na ML modelech, včetně plně interaktivního plátna s podporou plynulého pan/zoom (podobně jako u GeoGebra nebo webových map).
(Poznámka: HLAVNÍ knihovnou projektu je PySide6)

---

## Hlavní funkce

### 1. Správa Sessions (Browser-like Tabs)

- Moderní správa relací (sessions) s novými kartami (záložkami) – chování inspirované webovými prohlížeči (Chrome, Firefox).
- Možnost pojmenovávat různé pracovní plochy.
- Dedikované tlačítko `+` na konci lišty pro rychlé vytvoření další relace.
- Rychlé zobrazení a přeskočení kroků při **New Session with File** přímo z lokálního disku s automatickým začleněním snímku do workflow.

### 2. Dynamické a interaktivní plátno obratlů (Image Canvas)

- **Pixel-perfect mapování:** Původní pixely obrázku se perfektně synchronizují s umístěním identifikovaných bodů.
- **Pohyb na plátně (Pan & Zoom):** Přehledné scrollování a pohyb po snímku (středové tlačítko myši, Spacebar + drag).
- **Auto-Focus bodů:** Kliknutím na jakýkoli bod ze seznamu dojde ke smooth přiblížení na příslušné místo (zoom box indikátor hlásí aktuální lupu).
- **Hard Bounds Clamp:** Pan control má plynulé dorazy, scrollování nevystřelí fotku mimo obrazovku a nenechá na prázdno.
- Stylizované barvy bodů pro snadnou identifikaci: (Pink, Light Green, Light Blue, Light Yellow, atd.)
- Zářivě "radioaktivně zelené" názvy pro dobrou viditelnost proti temnému pozadí X-ray snímků.

### 3. ML Workflow (Simulator)

- Modální inference simulující dva modely.
- Načtení, validace, extrakce a vizualizace vertebrálních metrik do přehledné tabulky.

### 4. Precizní úpravy souřadnic u bodů

- **Mouse Drag-and-drop:** Body je možné manuálně přetáhnout a doladit tak nepřesnosti ML modelu.
- **Klávesové šipky:** Jemné doladění bodů (1px posun, se `Shift` klávesou 5px posun).
- **Live Sync:** Změny umístění bodů se okamžitě reflektují mezi uživatelským rozhraním v tabulce, plátnem a vnitřním stavem.
- **Reset Button :** Možnost vrátit každý bod individuálně na specifickou původní souřadnici vyčíslenou ML modelem před lidským zásahem.

---

## Požadavky a Instalace

Pro běh aplikace je vyžadován **Python 3.10+** (doporučeno využití virtuálního prostředí venv).

1. Naklonujte si tento repozitář:

```bash
git clone <url_repozitare>
cd DigiTech-Spiner-PySide-GUI-Project
```

1. Nainstalujte příslušné dependencies přes PIP:

```bash
pip install -r requirements.txt
```

1. Spuštení aplikace:

```bash
python main.py
```

---

## Struktura repozitáře

- `main.py` – Vstupní bod, spouští smyčku Qt aplikace.
- `config.py` – Konfigurační konstanty aplikace. Nastavuje velikosti vykreslovaných elementů, barvy či logiku nápisů (`USE_ABBREVIATED_LABELS`).
- `logger.py` – Centrální app loggování.
- `ui/`
  - `main_window.py` – Wrapper držící logiku struktury karet (Tabs) s nativně řešeným tlačítkem `+`.
  - `session_screen.py` – Samotná obrazovka pracovního místa obratlů, řešící obousmernou state-logiku (co je k dispozici během vizualizace/nastavení).
  - `panels/`
    - `drag_drop_frame.py` – Handler pro zachytávání "drag & drop" obrázků napříč OS.
    - `image_canvas_panel.py` – Nejkomplexnější třída scény a grafického zobrazení (zoom/bounds logik a focus trigger).
    - `points_panel.py` – Boční control panel (seznam tabulek pro editaci metrik a resety jednotlivých bodů).
- `core/`
  - `io.py` a `models.py` – Třídy zastupující simulaci inference ML operací, parsování JSON výstupů a ukládání formátu bodů do abstraktních struktur.

---

## Fáze Vývoje (Status)

Seznam funkcí dle Development roadmapy:

- **Phase 1:** Canvas Setup + Rendering, Zoom/Pan controls.
- **Phase 2:** Selection + Highlighting obousměrná komunikace (výběr bodu v UI <=> plátno).
- **Phase 3.1:** Chytání a přesuny bodů myší, boundary check, Live Sync.
- **Phase 3.2:** Jemný posun pomocí klávesnicových šipek.
- **Phase 3.3:** Reset tlačítka na původní ML souřadnice.
- **Phase 3.4:** Deep bug fixing v synchronizaci dat v signálových řetězcích `pointMoved()`.
- **Phase 4:** Kalkulace real-time biologických metrik z polygonů a úhlů těžiště.

---

## Rychlý návod

1. **Načtení X-ray snímku:**
   Můžete buď přetáhnout obrázek rovnou do šedé zóny ("Drag a drop") na čisté Session obrazovce, nebo využít z File menu vlevo nahoře metodu "New Session with file", která vás automatický proklikne rovnou do načtení (auto-skip import dialogu).
2. **Inference model:**
   Klikněte na „Spustit Inferenci“, což nasimuluje detekci. Na rentgenu by se měly vykreslit puntíky.
3. **Editace Bodů:**
   Kliknutím na tlačítko "Body" se dostanete do seznamu. Klikněte na jakkoliv nalezený bod v seznamu a plátno se tam plynule přiblíží. Bod můžete popadnout myší, nebo ho jemně dotáhnout klávesnicovými šipkami.
4. **Vlastní konfigurace (Vývojářská):**
   Otevřete `config.py` pokud chcete rušit plná anglická slova na body (měnit na zkratky: 'TL', 'BR', apod.), nebo zvětšovat poloměry vykreslovaných bodů.

---

Vytvořeno od: *Life-Hard-by-Work-Smart* & *GitHub Copilot*.
Aktuální focus branch: `experimental`.

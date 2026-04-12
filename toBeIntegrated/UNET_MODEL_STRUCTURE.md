# UNet Model Integration - Struktura a Popis

## 📋 Přehled

Složka `toBeIntegrated/` obsahuje produkční implementaci **U-Net segmentačního modelu** pro detekci vertebrálních obratlů v rentgenových snímcích. Projekt se skládá ze tří hlavních komponent: **Atlas** (model a dataset), **Models** (trénovací infrastruktura) a **Utils** (pomocné funkce).

Model byl trénován na **multi-class segmentaci** s 7 třídami (6 obratlů + background) s podporou **patch-based inference** pro efektivní zpracování velkých obrázků.

---

## 🏗️ Stromová struktura

```
toBeIntegrated/
├── README.md                              # Základní dokumentace
├── exploratory/                           # Experimentální Python notebooky
├── Src/
│   ├── Models/
│   │   ├── Atlas-heqv-multi-patch-10000-fold-0-final.pth  # Trénovaná váha (hlavní model)
│   │   ├── training_new.py                # Trénovací smyčka
│   │   └── testing.py                     # Testovací skript
│   │
│   ├── Atlas/
│   │   ├── atlas_dataset_patch.py         # Custom PyTorch Dataset
│   │   ├── atlas_model_multiclass_patch.py# Training pipeline
│   │   ├── atlas_test_multiclass_patch.py # Testing pipeline
│   │   ├── batch_inference.py             # Inference na více souborech
│   │   ├── single_inference.py            # Inference na jednom snímku (CRITICAL)
│   │   ├── keypoint_extraction.py         # Extrakce 5bodů z masky (CRITICAL)
│   │   └── draw_metrics.py                # Vizualizace výsledků
│   │
│   └── Utils/
│       ├── replicability.py               # Seed management (reprodukovatelnost)
│       ├── data_utils.py                  # Dataset loading helpers
│       ├── image_utils.py                 # Image preprocessing
│       ├── metrics.py                     # Evaluační metriky (Dice, IoU)
│       ├── loss_plotter.py                # Trénovací loss vizualizace
│       └── dice_plotter.py                # Dice skóre grafy
```

---

## 📦 Detailní Popis Souborů

### **Models/** - Trénovací infrastruktura

#### `Atlas-heqv-multi-patch-10000-fold-0-final.pth`

- **Typ:** PyTorch model checkpoint (váhy modelu)
- **Velikost:** ~100-200 MB (přesnou velikost viz soubor)
- **Architektura:** UNet s input (3 kanály - RGB), output (7 tříd - segmentace)
- **Trénink:** 10000 obrázků, histogram equalization preprocessing, fold-0 cross-validation
- **Status:** ✅ Hotov a připraven k použití
- **Odkaz v kódu:** `atlas_model_multiclass_patch.py:config["NAME"]`

#### `training_new.py`

- **Účel:** Centrální trénovací logika
- **Funkce:**
  - `load_model()` – Načtení trénovaného modelu ze `.pth` souboru
  - `training_loop()` – Hlavní trénovací smyčka (epochs, loss, backprop)
  - `save_model()` – Uložení checkpoint během tréninku
- **Dependency:** PyTorch, MONAI, torch.optim
- **Použití:** Importováno z `atlas_model_multiclass_patch.py`

#### `testing.py`

- **Účel:** Testování modelu na validation setu
- **Výstupy:** Metriky (Dice score, IoU), loss
- **Použití:** Evaluace modelu během a po tréninku

---

### **Atlas/** - Core Model + Inference

#### `atlas_model_multiclass_patch.py` ⭐ PRIORITA 1

- **Účel:** Konfigurační a trénovací pipeline
- **Klíčové prvky:**

  ```python
  config = {
    "NAME": "Atlas-heqv-multi-patch-10000",
    "NUM_CLASSES": 7,              # 6 obratlů + 1 background
    "BINARY": False,               # Multi-class mode
    "MAX_EPOCHS": 200,             # Délka tréninku
    "LR": 1e-2,                    # Learning rate
    "TRAIN_BATCH_SIZE": 2,
    "TEST_BATCH_SIZE": 2,
    "SEED": 42,                    # Pro reprodukovatelnost
  }
  ```

- **Model:** `UNet` z MONAI
- **Transformace:**
  - Histogram Equalization (zlepšení kontrastu X-raye)
  - ScaleIntensity (normalizace hodnot pixelů)
  - SpatialPad (550x550)
  - RandSpatialCrop (512x512 patch)
  - Augmentace: flip, rotate, zoom, gaussian noise
- **Loss:** `DiceCELoss` (kombinace Dice a Cross Entropy)
- **Optimizátor:** SGD/Adam (dle konfigurace)

#### `atlas_dataset_patch.py`

- **Účel:** Custom PyTorch `Dataset` třída
- **Hlavní třída:** `AtlasDataset`
- **Input:** Cesty na X-ray PNG + маски (label PNG)
- **Output:** `{"image": tensor, "label": tensor}` dict
- **Preprocessing:** Histogram equalization, padding, cropping
- **Augmentace:** RandFlip, RandRotate, RandZoom aplikované dynamicky

#### `single_inference.py` ⭐⭐ PRIORITA 1 (NEJDŮLEŽITĚJŠÍ)

- **Účel:** Inference na JEDNOM snímku – **toto je to, co potřebujeme integrovat!**
- **Klíčové funkce:**
  - `load_model()` – Načtení `.pth` váhy
  - `preprocess_image()` – Histogram equalization, normalizace
  - `inference()` – Forward pass s `sliding_window_inference` (512x512 patche)
  - `postprocess()` – Morfologické operace (opening, closing, fill_holes)
  - Výstup: **Maska ve formátu (H, W) s hodnotami 0-6 (třídy)**
  - Výstup: **Barevná reprezentace masky RGB(H, W, 3)**
  - Výstup: **Blended overlay (původní obrázek + maska)**
- **CLI příkaz:**

  ```bash
  python .\Src\Atlas\single_inference.py \
    --model_path .\Src\Models\Atlas-heqv-multi-patch-10000-fold-0-final.pth \
    --image_path .\Tests\0001035.png \
    --output_dir .\Tests\ \
    --no_blend
  ```

- **Output formáty:**
  - Numpy array maska (uint8, 0-6)
  - PNG obrázek s barvami
  - JSON se souřadnicemi bodů (pokud je zapnuta extrakce)

#### `keypoint_extraction.py` ⭐⭐ PRIORITA 1 (EXTRAKCE BODŮ)

- **Účel:** Extrakce 5bodů (4 rohy + centroid) z každého obratlenu (segmentační masky)
- **Klíčové funkce:**
  - `unique_colors_bgr()` – Získání unikalních barev z maskované mapy
  - `mask_from_color()` – Vytvoření binární masky pro jednu třídu
  - `clean_binary()` – Morfologické čištění (erosion, dilation)
  - `main_contour()` – Získání hlavního obrysu každé třídy
  - `approx_poly_n()` – Aproximace kontury na N vrcholů (4 rohy = quad)
  - **Centroid calculation:** Těžiště každé objektu (mean X, Y)
  - **Output:** JSON s body: `{"TL": [x, y], "TR": [...], "BL": [...], "BR": [...], "C": [...]}`
- **Workflow:**
  1. Ze segmentační masky (7 tříd)
  2. Pro každou třídu (obratel 1-6)
  3. Detekuj hlavní konturu
  4. Aproximuj na 4 vrcholy (quadrilateral)
  5. Vypočítej těžiště (centroid)
  6. Vrať 5bodů v JSON

#### `batch_inference.py`

- **Účel:** Inference na více souborech najednou
- **Input:** Adresář s PNG obrázky
- **Output:** Adresář s maskami a bodovými výstupy
- **Uso:** `python batch_inference.py --input_dir ./images --output_dir ./results --model_path ./model.pth`

#### `atlas_test_multiclass_patch.py`

- **Účel:** Testovací/validační pipeline
- **Výstup:** Metriky (Dice, IoU, sensitivity, specificity)

#### `draw_metrics.py`

- **Účel:** Vizualizace predikčních metrik
- **Výstup:** Tabulky a grafy s výsledky

---

### **Utils/** - Pomocné funkce

#### `replicability.py` ⭐ PRIORITA 2

- **Účel:** Zajištění reprodukovatelnosti modelu
- **Funkce:**
  - `set_seed(seed)` – Nastaví seed pro random, numpy, PyTorch, CUDA
  - `make_worker_seed_fn(seed)` – Seed pro workers v DataLoaderech
  - `get_generator(seed)` – PyTorch generator se stanoveným seedem
- **Použití:** Zavolej `set_seed(42)` na začátku pro konzistentní výsledky
- **Proč:** Různé knihovny (NumPy, PyTorch) mají své generátory, všechny je třeba nastavit

#### `image_utils.py`

- **Transformace:**
  - `HistogramEqualizationd` – MONAI transformace pro vylepšení kontrastu
  - Ostatní image preprocessing (resize, normalize, pad)

#### `data_utils.py`

- **Účel:** Třídění datasetu do foldů (k-fold cross-validation)
- **Funkce:**
  - `create_fold_info()` – Inicializace struktury fold-infa
  - `get_split_files()` – Rozdělení souborů do train/val
  - `fill_fold_info()` – Vyplnění fold struktury cestami

#### `metrics.py`

- **Metriky:**
  - Dice score (segmentační kvalita)
  - Intersection over Union (IoU)
  - Sensitivity / Specificity
  - Accuracy
- **Výpočet:** Pixel-wise porovnání predikce vs ground truth

#### `loss_plotter.py`

- **Účel:** Vizualizace loss curves během tréninku
- **Výstup:** Grafy zobrazující convergenci modelu

#### `dice_plotter.py`

- **Účel:** Vizualizace Dice skóre během tréninku
- **Výstup:** Grafy zobrazující kvalitu predikce

---

## 🔄 Tok dat - Jak model pracuje

### Training (offline, už je hotov)

```
X-ray PNG → Histogram Equalization → Normalizace → Padding
  ↓
Labels (segmentační masky PNG) → Převod na třídy (0-6)
  ↓
PyTorch Dataset + DataLoader (s augmentací)
  ↓
UNet Model (3 input channels → 7 output channels)
  ↓
DiceCELoss + SGD Optimizer
  ↓
Checkpoints uloženy (Atlas-heqv-multi-patch-10000-fold-0-final.pth) ✅
```

### Inference (TO-DO integrovat do GUI!)

```
Input: X-ray PNG cesta
  ↓
single_inference.py:
  ├─ Načtení modelu ze .pth
  ├─ Preprocessing (histogram eq, normalizace)
  ├─ Sliding window inference (512x512 patche)
  ├─ Postprocessing (morfologie, fill holes)
  └─ Output: Maska (H, W, 0-6) + Kontury
  ↓
keypoint_extraction.py:
  ├─ Pro každou třídu (obratel 1-6):
  │  ├─ Detekce kontur
  │  ├─ Aproximace na 4 rohy (quad)
  │  └─ Výpočet centroidu
  └─ Output: JSON s 5 body per obratel → {"TL": [x,y], ...}
  ↓
GUI (SessionScreen):
  ├─ Zobrazení masky na canvas
  ├─ Zobrazení 5bodů na canvas
  └─ Možnost editace souřadnic (drag, šipky, reset)
```

---

## 🔧 Integration Roadmap (PLÁN)

### Fáze 1: Příprava

- [ ] Zkopíruj `Src/Atlas/single_inference.py` do `core/ml_models/`
- [ ] Zkopíruj `Src/Atlas/keypoint_extraction.py` do `core/ml_models/`
- [ ] Zkopíruj váhu (`*.pth`) do `core/ml_models/weights/`
- [ ] Zkopíruj `Src/Utils/replicability.py` do `core/utils/`
- [ ] Zkopíruj `Src/Utils/image_utils.py` do `core/utils/`

### Fáze 2: Adaptace

- [ ] Refaktoruj `single_inference.py` – odděl CLI logiku od core inference
- [ ] Vytvořit wrapper třídu: `AtlasUNetModel(model_path)` s metodou `inference(image_path) → maska`
- [ ] Refaktoruj `keypoint_extraction.py` – vytvoř `extract_keypoints(maska, num_classes=7) → json_dict`

### Fáze 3: GUI Integrace

- [ ] V `core/ml_inference.py` (nebo `core/models.py`):
  - Nahraď simulátor `MLInferenceSimulator()` na `AtlasUNetModel()`
  - Integruj `extract_keypoints()` do pipeline
- [ ] V `ui/session_screen.py`:
  - Při kliknutí "Spustit Inferenci": zavolej `model.inference(image_path)`
  - Přijmi masku + JSON s body
  - Pass body do `canvas_panel` a `vertebral_panel`
- [ ] Testování end-to-end na skrze GUI

### Fáze 4: Optimalizace (futures)

- [ ] GPU support (CUDA device management)
- [ ] Caching modelu v paměti (neloadovat znovu)
- [ ] Progress bar pro dlouhé inference
- [ ] Error handling (bad image format, model crash)

---

## 📊 Model Architektura - UNet

```
Input: (B, 3, 512, 512)     # Batch size, 3 RGB kanály, 512x512
  ↓
Encoder (konvoluční downsampling):
  ├─ Conv 3→64
  ├─ MaxPool 2x2
  ├─ Conv 64→128
  ├─ MaxPool 2x2
  ├─ Conv 128→256
  └─ MaxPool 2x2
  ↓
Bottleneck: Conv 256→512
  ↓
Decoder (upsampling + skip connections):
  ├─ UpConv 512→256 + skip
  ├─ UpConv 256→128 + skip
  ├─ UpConv 128→64 + skip
  └─ Conv 64→7
  ↓
Output: (B, 7, 512, 512)    # 7 segmentačních tříd
  ↓
Postprocessing:
  ├─ argmax(dim=1) → (B, 512, 512) s hodnotami 0-6
  ├─ Morfologické operace
  └─ Fill holes → finální maska
```

---

## ⚙️ Dependencies

```txt
torch>=1.13.0
torchvision>=0.14.0
monai>=0.9.0            # Medical image library (UNet, transforms, loss)
numpy>=1.21.0
opencv-python>=4.5.0
scipy>=1.7.0            # Morfologické operace
scikit-image>=0.19.0    # Contour detection
Pillow>=8.0.0           # Image I/O
pandas>=1.3.0           # Data manipulation (cross-validation)
```

---

## 🚀 Quick Start (CLI Test)

Pro testování modelu MIMO GUI - **kompletní pipeline s inferencí + extrakcí bodů**:

**PowerShell (Windows):**

```powershell
cd toBeIntegrated/

# Definuj proměnné
$modelPath = ".\Src\Models\Atlas-heqv-multi-patch-10000-fold-0-final.pth"
$imagePath = "../testing_data/0001035_image.png"
$outputDir = "../testing_data/outputs/"
$inputFileName = [System.IO.Path]::GetFileNameWithoutExtension($imagePath)

# Fáze 1: Single image inference (vytvoří masku)
python Src/Atlas/single_inference.py `
  --model_path $modelPath `
  --image_path $imagePath `
  --output_dir $outputDir `
  --no_blend

# Fáze 2: Keypoint extraction (extrahuje 5 bodů z masky do JSON)
python Src/Atlas/keypoint_extraction.py `
  --in "$outputDir" `
  --out_dir "$outputDir" `
  --pattern "*_maskhat.png" `
  --verbose

# Output:
#   - mask.png
#   - colored_mask.png
#   - blended.png
#   - keypoints.json (s 5 body: TL, TR, BL, BR, C)
```

**Bash (Linux/Mac):**

```bash
cd toBeIntegrated/

# Definuj proměnné
MODEL_PATH="./Src/Models/Atlas-heqv-multi-patch-10000-fold-0-final.pth"
IMAGE_PATH="../testing_data/0001035_image.png"
OUTPUT_DIR="../testing_data/outputs/"
INPUT_FILE=$(basename "$IMAGE_PATH" .png)

# Fáze 1: Single image inference (vytvoří masku)
python Src/Atlas/single_inference.py \
  --model_path $MODEL_PATH \
  --image_path $IMAGE_PATH \
  --output_dir $OUTPUT_DIR \
  --no_blend

# Fáze 2: Keypoint extraction (extrahuje 5 bodů z masky do JSON)
python Src/Atlas/keypoint_extraction.py \
  --in "$OUTPUT_DIR" \
  --out_dir "$OUTPUT_DIR" \
  --pattern "*_mask.png" \
  --verbose

# Output:
#   - mask.png
#   - colored_mask.png
#   - blended.png
#   - keypoints.json (s 5 body: TL, TR, BL, BR, C)
```

**Nebo použij PowerShell script (all-in-one):**

```powershell
# Spusť nastavený pipeline script
.\inference_pipeline.ps1 `
  -ImagePath "../testing_data/0001035_image.png" `
  -ModelPath ".\Src\Models\Atlas-heqv-multi-patch-10000-fold-0-final.pth" `
  -OutputDir "../testing_data/outputs/" `
  -Verbose
```

---

## 📝 TODO - Aktuální Status

- [x] Model trénovaný a uložený (`.pth`)
- [x] Single inference script hotov
- [x] Keypoint extraction hotov
- [ ] **Integrovat do GUI** (next phase)
- [ ] Testovat na reálných X-ray snímcích
- [ ] Optimalizovat pro real-time inference
- [ ] Přidat GPU management
- [ ] Dokumentovat deployment

---

## 🎯 Kontakt / Další Otázky

Pokud máš otázky na konkrétní soubor nebo mechaniku:

1. Detailní popis je výše v sekcích
2. Kód je samozřejmě v repozitáři s komentáři
3. Plán integrace je ve Fázi 1-4 výše

---

### Let's go! 🚀

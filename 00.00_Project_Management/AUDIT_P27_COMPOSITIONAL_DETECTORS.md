# تدقيق معماري: دمج mrkdwn_analysis في Prism Stage 2

## المبدأ المعماري: مسار توحيدي تجميعي (Compositional Unified Path)

**بدلاً من:** dual-path (Prism default → mrkdwn_analysis fallback)
**نحو:** detector واحد يركّب الأفضل من الاثنين via composition + wrapping

### قاعدة التركيب
```
CompositionalDetector = Prism(AST) + mrkdwn_analysis(wrapped method)
                       ↓
                    مستكشف واحد شامل
                    يعود بـ LayerInstance موحّد
```

---

## 1. تصنيف الديتيكتورز الحالية: ما يحتاج تحديث vs ما يبقى كما هو

### 🔴 يحتاج تحديث تركيبي (Compositional Update) — 5 ديكتكتورز

| # | الديتيكتور الحالي | المصدر المستهدف من mrkdwn_analysis | ما نأخذه | ما نبقيه من Prism | الاسم المقترح |
|---|-------------------|-----------------------------------|----------|-------------------|---------------|
| 1 | `ASTCodeBlockDetector` | `parse_indented_code_block()` | كشف indented code (4 spaces/tabs) | AST للـ fenced code blocks (أدق) | `UnifiedCodeBlockDetector` |
| 2 | `RegexHTMLBlockDetector` | `is_html_block_start()` + `parse_html_block()` + BeautifulSoup | حدود HTML blocks عبر blank line + HTML comments | استخراج `tag_name` + `is_semantic` + attributes | `UnifiedHTMLBlockDetector` |
| 3 | `LibraryHTMLInlineDetector` | `identify_html_inline()` (BeautifulSoup) | كشف العناصر الكاملة `<span class="x">text</span>` كوحدة | فلتر block tags + استخراج attributes + char offsets | `UnifiedHTMLInlineDetector` |
| 4 | `RegexLinkDetector` | `references` dict + `REFERENCE_DEF_RE` | Reference links `[text][id]` + `[id]: url` | Inline links + Auto-links + `is_external` + `domain` | `UnifiedLinkDetector` |
| 5 | `HybridFootnoteDetector` | `footnotes` dict + `_parse_inline_tokens` | تتبع footnote references في النص `[^id]` | AST detection + raw text fallback للـ definitions | `UnifiedFootnoteDetector` |

### 🟡 يحتاج تحديث بسيط (Prism-only Enhancement) — 2 ديتكتور

| # | الديتيكتور الحالي | التحديث المطلوب | الاسم المقترح |
|---|-------------------|----------------|---------------|
| 6 | `ASTListDetector` | إضافة كشف task items `- [ ]` / `- [x]` داخل AST list nodes | `UnifiedListDetector` |
| 7 | `ASTBlockquoteDetector` | دعم nested blockquotes عبر AST children (موجود بالفعل، يحتاج تأكيد) | يبقى `ASTBlockquoteDetector` |

### ✅ لا يحتاج تغيير — 8 ديتكتورز

| # | الديتيكتور | السبب |
|---|-----------|-------|
| 8 | `ASTHeadingDetector` | Prism AST أدق من regex |
| 9 | `ASTParagraphDetector` | متكافئ — AST أفضل |
| 10 | `ASTTableDetector` | Prism يحلل أعمق (cells, headers) |
| 11 | `HeuristicDiagramDetector` | Prism حصري — mrkdwn_analysis لا يدعم |
| 12 | `RegexFigureDetector` | Prism أفضل فصل (طبقة مستقلة) |
| 13 | `RegexInlineCodeDetector` | Prism يدعم double backtick |
| 14 | `RegexEmphasisDetector` | Prism يدعم strikethrough + type detection |
| 15 | `HybridMetadataDetector` | متكافئ — Prism يعرض كـ LayerInstance |

---

## 2. ديتكتورز جديدة من الصفر (New Creation) — 3 ديتكتورز

| # | الديتيكتور الجديد | LayerType الجديد | المصدر | الوصف |
|---|-------------------|-----------------|--------|-------|
| A | `UnifiedTaskListDetector` | `TASK_LIST` | mrkdwn_analysis `identify_task_items()` | كشف `- [ ]` / `- [x]` كطبقة مستقلة |
| B | `UnifiedHRDetector` | `HORIZONTAL_RULE` | mrkdwn_analysis `HR_RE` + Prism | كشف `---`, `***`, `___` |
| C | `UnifiedSectionDetector` | `SECTION` | mrkdwn_analysis `identify_sections()` | كشف Setext sections (text + ===/---) |

---

## 3. الخطة التنفيذية بالتفصيل

### المرحلة 1: تحديث الـ enums والـ contracts

**ملفات تتأثر:**
- `prism/schemas/enums.py` — إضافة 3 LayerTypes جديدة: `TASK_LIST`, `HORIZONTAL_RULE`, `SECTION`
- `prism/schemas/physical.py` — إضافة 3 typed component models
- `prism/schemas/__init__.py` — exports
- `prism/stage2/layers/detectors.py` — إضافة 3 ABC contracts جديدة

### المرحلة 2: تحديث 5 ديكتكتورز تركيبية

#### 2.1 `UnifiedCodeBlockDetector`
```
التركيبة:
  Prism AST (NodeType.CODE_BLOCK) → fenced code
  + mrkdwn_analysis parse_indented_code_block() → indented code
  + Prism diagram filter → استبعاد mermaid/graphviz
```

#### 2.2 `UnifiedHTMLBlockDetector`
```
التركيبة:
  mrkdwn_analysis MarkdownParser.is_html_block_start() → boundary detection
  mrkdwn_analysis MarkdownParser.parse_html_block() → content extraction
  + Prism tag_name extraction + is_semantic classification + attributes parsing
```

#### 2.3 `UnifiedHTMLInlineDetector`
```
التركيبة:
  mrkdwn_analysis InlineParser (BeautifulSoup) → full element detection
  + Prism _BLOCK_TAGS filter → استبعاد block tags
  + Prism char offset computation → LayerInstance مع offsets صحيحة
  + Prism is_self_closing detection
```

#### 2.4 `UnifiedLinkDetector`
```
التركيبة:
  Prism inline regex → [text](url) + <url>
  + mrkdwn_analysis references dict → [text][ref] + [ref]: url
  + Prism is_external + domain extraction
```

#### 2.5 `UnifiedFootnoteDetector`
```
التركيبة:
  Prism AST detection → footnote definitions
  + Prism raw text fallback → [^label]: content
  + mrkdwn_analysis _parse_inline_tokens → footnote references في النص
  → attributes: {"label": "...", "has_reference": "..."}
```

#### 2.6 `UnifiedListDetector`
```
التركيبة:
  Prism AST (NodeType.LIST) → ordered/unordered
  + mrkdwn_analysis task_re pattern → task items داخل lists
  → attributes: {"style": "...", "has_tasks": "...", "task_count": "..."}
```

### المرحلة 3: إنشاء 3 ديتكتورز جديدة

#### 3.1 `UnifiedTaskListDetector`
```
المصدر: mrkdwn_analysis identify_task_items()
المنطق:
  - scan all list tokens
  - for each item with task_item=True
  - produce LayerInstance with attributes: {"checked": "...", "text": "..."}
```

#### 3.2 `UnifiedHRDetector`
```
المصدر: mrkdwn_analysis HR_RE + Prism raw text scanning
المنطق:
  - regex ^(\*{3,}|-{3,}|_{3,})\s*$
  - produce LayerInstance with attributes: {"style": "asterisk"|"dash"|"underscore"}
```

#### 3.3 `UnifiedSectionDetector`
```
المصدر: mrkdwn_analysis Setext section detection
المنطق:
  - detect text line followed by === (H1 section) or --- (H2 section)
  - produce LayerInstance with attributes: {"level": "1"|"2", "title": "..."}
```

### المرحلة 4: Wiring

- `prism/stage2/classifier.py` — تحديث `_ALL_DETECTORS` list
- `prism/stage2/layers/__init__.py` — exports
- `prism/stage2/layers/nesting.py` (NestingMatrix) — تحديث قواعد الـ nesting للـ 3 types الجديدة
- `prism/stage2/layers/simple_layers.py` — إضافة 3 CRUDs جديدة

---

## 4. خريطة الملفات المتأثرة

| الملف | التغيير | الأولوية |
|-------|---------|----------|
| `prism/schemas/enums.py` | +3 LayerTypes | 🔴 High |
| `prism/schemas/physical.py` | +3 typed components + NestingMatrix | 🔴 High |
| `prism/schemas/__init__.py` | exports | 🔴 High |
| `prism/stage2/layers/detectors.py` | +3 contracts | 🔴 High |
| `prism/stage2/layers/specific_detectors.py` | تحديث 5 + إضافة 3 | 🔴 High |
| `prism/stage2/layers/__init__.py` | exports | 🔴 High |
| `prism/stage2/layers/simple_layers.py` | +3 CRUDs | 🟡 Medium |
| `prism/stage2/classifier.py` | تحديث _ALL_DETECTORS | 🔴 High |
| `tests/test_inline_detectors.py` | تحديث tests | 🔴 High |
| `tests/test_layer_crud.py` | +3 CRUD tests | 🟡 Medium |
| `tests/test_schemas_detection.py` | +3 type tests | 🟡 Medium |
| `tests/test_stage2_orchestration.py` | تحديث orchestration | 🟡 Medium |
| `tests/test_schemas_typed_components.py` | +3 component tests | 🟡 Medium |

---

## 5. ملخص الأرقام

| الفئة | العدد |
|-------|-------|
| ديكتكتورز موجودة لا تحتاج تغيير | 8 |
| ديكتكتورز تحتاج تحديث تركيبي | 5 |
| ديكتكتورز جديدة من الصفر | 3 |
| LayerTypes جديدة | 3 |
| ABC contracts جديدة | 3 |
| Typed component models جديدة | 3 |
| CRUD classes جديدة | 3 |
| **إجمالي الديتيكتورز بعد التحديث** | **18** (كانت 15) |

---

## 6. قرار التوثيق: mrkdwn_analysis كـ third_party

```
prism/third_party/mrkdwn_analysis/
├── mrkdwn_analysis/
│   ├── __init__.py
│   ├── markdown_analyzer.py  ← السورس الأساسي
│   └── mrkdwntool.py
└── LICENSE  ← MIT
```

**الاستراتيجية:**
- لا نُعيد كتابة منطق mrkdwn_analysis
- نwrapp الكلاسات المطلوبة فقط (`MarkdownParser`, `InlineParser`, `MarkdownAnalyzer`)
- نستخدم الـ methods الداخلية مباشرة (`parse_indented_code_block`, `is_html_block_start`, إلخ)
- الـ import يكون من `prism.third_party.mrkdwn_analysis.mrkdwn_analysis.markdown_analyzer`

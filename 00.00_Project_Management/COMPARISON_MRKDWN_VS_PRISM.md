# مقارنة شاملة: mrkdwn_analysis vs Prism Stage 2

## 1. جدول تغطية الظواهر (Elements/Features Coverage)

| # | الظاهرة | mrkdwn_analysis | Prism Stage 2 | ملاحظات |
|---|---------|----------------|---------------|---------|
| 1 | **Headings** (ATX + Setext) | ✅ `identify_headers()` | ✅ ASTHeadingDetector | Prism يحدد level من AST مباشرة |
| 2 | **Paragraphs** | ✅ `identify_paragraphs()` | ✅ ASTParagraphDetector | متكافئ |
| 3 | **Tables** (GFM) | ✅ `identify_tables()` — header + rows | ✅ ASTTableDetector | Prism يحلل rows → cells → TableCell |
| 4 | **Lists** (ordered/unordered) | ✅ `identify_lists()` | ✅ ASTListDetector | Prism يدعم nesting في AST |
| 5 | **Task Lists** | ✅ `identify_task_items()` | ❌ **لا يوجد** | **فجوة في Prism** |
| 6 | **Code Blocks** (fenced + indented) | ✅ `identify_code_blocks()` — كلا النوعين | ✅ ASTCodeBlockDetector — fenced فقط | **فجوة: Prism لا يدعم indented code** |
| 7 | **Blockquotes** | ✅ `identify_blockquotes()` | ✅ ASTBlockquoteDetector | متكافئ |
| 8 | **Metadata** (Front Matter YAML) | ✅ `parse_frontmatter()` — داخلي فقط | ✅ HybridMetadataDetector | Prism يعرضه كـ LayerInstance |
| 9 | **Footnotes** | ✅ `identify_footnotes()` | ✅ HybridFootnoteDetector | متكافئ |
| 10 | **Diagrams** (mermaid, etc.) | ❌ **لا يوجد** | ✅ HeuristicDiagramDetector | **ميزة Prism حصرية** |
| 11 | **Figures** (images) | ✅ عبر `identify_links()` كـ "Image link" | ✅ RegexFigureDetector | Prism يحدد كطبقة مستقلة |
| 12 | **Inline Code** | ✅ `identify_inline_code()` | ✅ RegexInlineCodeDetector | Prism يدعم double-backtick |
| 13 | **Emphasis** | ✅ `identify_emphasis()` — نص فقط | ✅ RegexEmphasisDetector | Prism يحدد النوع (bold/italic/strikethrough) + marker |
| 14 | **Links** (text + image + auto) | ✅ `identify_links()` | ✅ RegexLinkDetector | Prism يدعم auto-links `<url>` |
| 15 | **HTML Block** | ✅ `identify_html_blocks()` — BeautifulSoup | ✅ RegexHTMLBlockDetector | mrkdwn_analysis أدق في تحديد boundaries |
| 16 | **HTML Inline** | ✅ `identify_html_inline()` — BeautifulSoup | ✅ LibraryHTMLInlineDetector (المكتبة + regex) | **الأفضل: mrkdwn_analysis كـ default** |
| 17 | **Horizontal Rules** (---, ***) | ✅ يكتشفها داخلياً (`hr`) | ❌ **لا يوجد كـ LayerType** | **فجوة في Prism** |
| 18 | **Sections** (Setext) | ✅ `identify_sections()` | ❌ **لا يوجد** | **فجوة في Prism** |
| 19 | **Search/Filter** | ✅ `search_content()`, `filter_by_type()` | ❌ **لا يوجد** | أدوات بحث ليست كشف ظواهر |
| 20 | **Statistics** | ✅ `analyse()`, `count_words()`, etc. | ❌ **لا يوجد** | إحصائيات ليست كشف ظواهر |

---

## 2. مقارنة منطق الكشف (Detection Logic Comparison)

### 2.1 Headings

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| الطريقة | regex line-by-line: `ATX_HEADER_RE`, `SETEXT_H1_RE`, `SETEXT_H2_RE` | markdown-it-py AST | **Prism** — AST أدق |
| ATX (# to ######) | ✅ Regex `^(#{1,6})\s+(.*)$` | ✅ `NodeType.HEADING` + `node.level` | Prism |
| Setext (===, ---) | ✅ يكتشف Setext H1/H1 | ✅ عبر markdown-it-py | متكافئ |
| Line numbers | ✅ `token.line` | ❌ لا يوفر | **mrkdwn_analysis** |
| **القرار** | — | — | **Prism default** (AST أدق), mrkdwn_analysis fallback |

### 2.2 Tables

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| الطريقة | regex: `TABLE_SEPARATOR_RE` + line-by-line parsing | markdown-it-py AST + GFM plugin | **Prism** |
| تحليل الخلايا | بسيط: `split('|')` → list | معقد: `rows[] → cells[] → TableCell` | **Prism** — أعمق |
| header detection | ✅ | ✅ | متكافئ |
| **القرار** | — | — | **Prism default** |

### 2.3 Lists

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| الطريقة | regex line-by-line | markdown-it-py AST | متكافئ تقريباً |
| Task lists | ✅ `- [ ]`, `- [x]` → `task_item`, `checked` | ❌ **لا يدعم** | **mrkdwn_analysis** |
| Nested lists | ✅ يدعم ضمنياً عبر continuation | ✅ يدعم عبر AST children | **Prism** |
| **القرار** | — | — | **Prism default**, mrkdwn_analysis كـ fallback للـ task items |

### 2.4 Code Blocks

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| Fenced (```) | ✅ `FENCE_RE` + `parse_fenced_code_block()` | ✅ markdown-it-py AST `fence` | متكافئ |
| Indented (4 spaces) | ✅ `parse_indented_code_block()` | ❌ **لا يدعم** | **mrkdwn_analysis** |
| Language detection | ✅ `meta={"language": lang}` | ✅ `attributes.get("language")` | متكافئ |
| Anti-bounce | ❌ يرمي `ValueError` على unclosed | ✅ markdown-it-py يتعامل تلقائياً | **Prism** |
| **القرار** | — | — | **Prism default**, mrkdwn_analysis كـ fallback للـ indented code |

### 2.5 Inline Code

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| الطريقة | Regex `CODE_INLINE_RE = r'`([^`]+)`'` | Regex `r'``(.+?)``|`([^`]+)`'` | **Prism** |
| Double backtick | ❌ لا يدعم | ✅ يدعم | **Prism** |
| Line numbers | ✅ `{"line": token.line, "code": c}` | ❌ لا يوفر line | **mrkdwn_analysis** |
| **القرار** | — | — | **Prism default** (يدعم double backtick) |

### 2.6 Emphasis

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| الطريقة | Regex `EMPHASIS_RE` | Regex patterns متعددة | **Prism** |
| Bold (**text**) | ✅ | ✅ | متكافئ |
| Italic (*text*) | ✅ | ✅ | متكافئ |
| Strikethrough (~~text~~) | ❌ **لا يدعم** | ✅ يدعم | **Prism** |
| Bold+Italic (***text***) | ❌ يكتشفه كـ bold فقط | ✅ `bold_italic` type | **Prism** |
| يحدد النوع (bold vs italic) | ❌ يرجع النص فقط | ✅ يرجع `emphasis_type` + `marker` | **Prism** |
| **القرار** | — | — | **Prism default** (أغنى معلوماتياً) |

### 2.7 Links

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| الطريقة | Regex `IMAGE_OR_LINK_RE` | Regex `INLINE_LINK_RE` + `AUTO_LINK_RE` | **Prism** |
| Inline `[text](url)` | ✅ | ✅ | متكافئ |
| Auto-link `<url>` | ❌ لا يدعم | ✅ يدعم | **Prism** |
| Reference links | ✅ يدعم | ❌ لا يدعم | **mrkdwn_analysis** |
| Image links | ✅ كـ "Image link" | ✅ كـ FIGURE (طبقة مستقلة) | **Prism** — أفضل فصل |
| **القرار** | — | — | **Prism default** |

### 2.8 HTML Block

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| الطريقة | line-by-line: `HTML_BLOCK_START` → `parse_html_block()` | Regex `HTML_BLOCK_RE` multiline | **mrkdwn_analysis** |
| Boundary detection | ✅ يعتمد على blank line | ❌ Regex قد يخطئ في boundaries | **mrkdwn_analysis** |
| HTML comments | ✅ `<!-- ... -->` | ❌ لا يدعم | **mrkdwn_analysis** |
| Semantic tags | ❌ لا يصنف | ✅ `is_semantic` flag | **Prism** |
| Tag extraction | ❌ يرجع المحتوى فقط | ✅ `tag_name` + `attributes` | **Prism** |
| **القرار** | — | — | **mrkdwn_analysis default** (أدق في boundaries), Prism للـ attributes |

### 2.9 HTML Inline

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| الطريقة | BeautifulSoup `soup.find_all()` على محتوى كل token | Regex + BeautifulSoup (مدمج الآن) | **mrkdwn_analysis** |
| يكتشف كامل العنصر | ✅ `<span class="x">text</span>` كوحدة واحدة | Regex يكتشف كل tag منفصلاً | **mrkdwn_analysis** |
| Block tag filtering | ❌ لا يفلتر | ✅ يفلتر block tags | **Prism** |
| Attributes | ✅ عبر BeautifulSoup | ✅ عبر regex | **mrkdwn_analysis** أدق |
| **القرار** | — | — | **mrkdwn_analysis default** + Prism للـ block tag filtering |

### 2.10 Blockquotes

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| الطريقة | Regex `BLOCKQUOTE_RE = r'^(>\s?)(.*)$'` | markdown-it-py AST | **Prism** |
| Nested blockquotes | ❌ لا يدعم | ✅ يدعم عبر AST nesting | **Prism** |
| **القرار** | — | — | **Prism default** |

### 2.11 Footnotes

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| الطريقة | Regex `FOOTNOTE_DEF_RE` + tracking usage | Hybrid: AST + raw text regex | متكافئ |
| Footnote definitions | ✅ `\[^id\]: content` | ✅ نفس الطريقة | متكافئ |
| Footnote references | ✅ يتتبع الاستخدام في النص | ❌ لا يتتبع | **mrkdwn_analysis** |
| **القرار** | — | — | **Prism default**, mrkdwn_analysis لتعزيز الـ references |

### 2.12 Metadata (Front Matter)

| الجانب | mrkdwn_analysis | Prism Stage 2 | الأفضل |
|--------|----------------|---------------|--------|
| الطريقة | Regex `^---\s*$` → parse between delimiters | Hybrid: AST (NodeType.METADATA) + raw text fallback | متكافئ |
| **القرار** | — | — | **Prism default** |

---

## 3. الخلاصة: Default vs Fallback

| الظاهرة | Default | Fallback | السبب |
|---------|---------|----------|-------|
| **HEADING** | Prism (AST) | mrkdwn_analysis (regex) | AST أدق مع level مباشر |
| **PARAGRAPH** | Prism (AST) | mrkdwn_analysis (regex) | متكافئ — AST أفضل |
| **TABLE** | Prism (AST+GFM) | mrkdwn_analysis (regex) | Prism يحلل أعمق |
| **LIST** | Prism (AST) | mrkdwn_analysis (regex) | AST يدعم nesting أفضل |
| **TASK_LIST** | mrkdwn_analysis | — | Prism لا يدعم بعد |
| **CODE_BLOCK** | Prism (AST) | mrkdwn_analysis (regex) | AST أفضل للـ fenced + Prism يحتاج indented |
| **BLOCKQUOTE** | Prism (AST) | mrkdwn_analysis (regex) | AST يدعم nesting |
| **METADATA** | Prism (Hybrid) | mrkdwn_analysis (regex) | متكافئ |
| **FOOTNOTE** | Prism (Hybrid) | mrkdwn_analysis (regex) | متكافئ + mrkdwn_analysis للـ references |
| **DIAGRAM** | Prism (Heuristic) | — | Prism حصري |
| **FIGURE** | Prism (Regex) | mrkdwn_analysis (identify_links) | Prism أفضل فصل |
| **INLINE_CODE** | Prism (Regex) | mrkdwn_analysis (regex) | Prism يدعم double backtick |
| **EMPHASIS** | Prism (Regex) | mrkdwn_analysis (regex) | Prism يدعم strikethrough + type detection |
| **LINK** | Prism (Regex) | mrkdwn_analysis (regex) | Prism يدعم auto-links |
| **HTML_BLOCK** | mrkdwn_analysis (BeautifulSoup) | Prism (Regex) | mrkdwn_analysis أدق في boundaries |
| **HTML_INLINE** | mrkdwn_analysis (BeautifulSoup) | Prism (Regex) | mrkdwn_analysis أدق |
| **HR** (Horizontal Rule) | mrkdwn_analysis | — | Prism لا يدعم بعد |
| **SECTION** (Setext) | mrkdwn_analysis | — | Prism لا يدعم بعد |

---

## 4. الفجوات المكتشفة في Prism

| الفجوة | الوصف | الأولوية |
|--------|-------|----------|
| Task Lists | Prism لا يكشف `- [ ]` / `- [x]` كطبقة | متوسطة |
| Indented Code Blocks | Prism لا يدعم 4-space indented code | متوسطة |
| Horizontal Rules | Prism لا يكشف `---`, `***`, `___` كطبقة | منخفضة |
| Sections (Setext) | Prism لا يحدد sections ككيان مستقل | منخفضة |

## 5. الفجوات المكتشفة في mrkdwn_analysis

| الفجوة | الوصف | التأثير |
|--------|-------|---------|
| لا يوجد AST | يعتمد على regex فقط | أقل دقة في المستندات المعقدة |
| لا يدعم Strikethrough | `~~text~~` غير مكتشف | فجوة وظيفية |
| لا يميز Bold vs Italic | يرجع النص فقط بدون نوع | يحتاج post-processing |
| لا يدعم Auto-links | `<url>` غير مكتشف | فجوة وظيفية |
| لا يفلتر Block tags من inline | `<div>` يظهر كـ inline HTML | يحتاج post-processing |
| لا يدعم Diagrams | mermaid/graphviz غير مكتشف | فجوة وظيفية |
| لا char offsets | يرجع line numbers فقط | غير كافٍ لـ token mapping |

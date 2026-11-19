"""Build the project report (Word) from the course template.

  python report/build_report.py            writes ../4th Year_UEMK_AI&ML_PROJECT REPORT FORMAT (2).docx  (template copy kept in report/template/)
  python report/measure.py                 exports a PDF with Word, finds each heading's page and stores it in pages.json; then build again

Pages 1 to 4 of the template (cover, certificate, acknowledgement, contents) stay as they are; only the project title and the table of contents change.
Figures: diagrams are drawn by make_diagrams.py, screenshots come from docs/images, and the machine-learning graphs are expected from the Colab notebook
in report/colab/ (save them in report/figures/colab/<key>.png; a yellow placeholder shows until a file exists).
"""

import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import docx_lib as D  # noqa: E402
import refs  # noqa: E402
from content import BLOCKS, TITLE, TITLE_CAPS  # noqa: E402

ROOT = HERE.parent
TEMPLATE = HERE / "template" / "template.docx"
import os
OUT = Path(os.environ["REPORT_OUT"]) if os.environ.get("REPORT_OUT") else ROOT / "4th Year_UEMK_AI&ML_PROJECT REPORT FORMAT (2).docx"
PAGES = json.loads((HERE / "pages.json").read_text()) if (HERE / "pages.json").exists() else {}
COLAB = HERE / "figures" / "colab"

# ------------------------------------------------------------------ numbering pass
fig_no, tab_no, eq_no, cite_order = {}, {}, {}, []
TOKEN = re.compile(r"\{(fig|tab|eq):([a-z0-9_]+)\}|\[@([a-z0-9_,;@ ]+)\]")


def scan(text):
    for m in TOKEN.finditer(text or ""):
        if m.group(3):
            for k in re.findall(r"[a-z0-9_]+", m.group(3).replace("@", " ")):
                if k not in cite_order:
                    cite_order.append(k)


def block_texts(b):
    kind = b[0]
    if kind in ("p", "pn", "h1", "h2", "h3", "code", "todo"):
        return [b[1]]
    if kind in ("bul", "num"):
        return list(b[1])
    if kind == "fig":
        return [b[3]]
    if kind == "colab":
        return [b[2]]
    if kind == "tab":
        return [b[2]] + [c for r in b[4] for c in r]
    return []


nf = nt = ne = 0
for b in BLOCKS:
    if b[0] == "fig":
        nf += 1
        fig_no[b[1]] = nf
    elif b[0] == "colab":
        nf += 1
        fig_no[b[1]] = nf
    elif b[0] == "tab":
        nt += 1
        tab_no[b[1]] = nt
    elif b[0] == "eq":
        ne += 1
        eq_no[b[1]] = ne
    for t in block_texts(b):
        scan(t)


def resolve(text):
    def sub(m):
        if m.group(1) == "fig":
            return f"Fig. {fig_no[m.group(2)]}"
        if m.group(1) == "tab":
            return f"Table {D.roman(tab_no[m.group(2)])}"
        if m.group(1) == "eq":
            return f"({eq_no[m.group(2)]})"
        keys = re.findall(r"[a-z0-9_]+", m.group(3).replace("@", " "))
        return ", ".join(f"[{cite_order.index(k) + 1}]" for k in keys)
    return TOKEN.sub(sub, text)


# ------------------------------------------------------------------ body
rels, media = [], {}
_rid = [200]


def add_image(path):
    path = Path(path)
    if str(path) in media:
        return media[str(path)][0]
    _rid[0] += 1
    rid = f"rId{_rid[0]}"
    name = f"image_r{_rid[0]}{path.suffix.lower()}"
    media[str(path)] = (rid, name, path)
    return rid


body, toc, lists = [], [], [0]
h1n = h2n = 0
for b in BLOCKS:
    k = b[0]
    if k == "h1":
        h1n += 1
        bm = f"_Toc9{h1n:03d}00"
        toc.append((1, b[1], bm))
        body.append(D.heading(1, b[1], bm))
    elif k == "h2":
        h2n += 1
        bm = f"_Toc9{h1n:03d}{h2n:02d}"
        toc.append((2, b[1], bm))
        body.append(D.heading(2, b[1], bm))
    elif k == "h3":
        body.append(D.heading(3, b[1], f"_Toc8{len(body):05d}"))
    elif k == "p":
        body.append(D.para(resolve(b[1]), first=360))
    elif k == "todo":
        body.append(D.para("[" + b[1] + "]", first=0, hl="yellow", i=True))
    elif k == "pn":
        body.append(D.para(resolve(b[1]), first=0))
    elif k == "bul":
        body.append(D.bullets([resolve(t) for t in b[1]]))
    elif k == "num":
        lists[0] += 1
        body.append(D.numbered([resolve(t) for t in b[1]], 20 + lists[0]))
    elif k == "code":
        for line in b[1].split("\n"):
            body.append(f'<w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="360"/><w:jc w:val="left"/></w:pPr>{D.run(line or " ", sz=18, font="Courier New")}</w:p>')
        body.append('<w:p><w:pPr><w:spacing w:before="0" w:after="120" w:line="240" w:lineRule="auto"/></w:pPr></w:p>')
    elif k == "fig":
        _, key, path, caption, width = b
        body.append(D.image_para(add_image(path), path, width, caption))
        body.append(D.figure_caption(fig_no[key], resolve(caption)))
    elif k == "colab":
        _, key, caption, desc, width = b
        f = COLAB / f"{key}.png"
        if f.exists():
            body.append(D.image_para(add_image(f), f, width, caption))
        else:
            body.append(D.placeholder(f"[Figure {fig_no[key]} goes here: {desc}. Run the Colab notebook and save the image as {key}.png]"))
        body.append(D.figure_caption(fig_no[key], resolve(caption)))
    elif k == "tab":
        _, key, caption, header, rows, widths, *rest = b
        align = rest[0] if rest else None
        body.append(D.table_caption(tab_no[key], resolve(caption)))
        body.append(D.table([resolve(h) for h in header], [[resolve(str(c)) for c in r] for r in rows], widths, align=align))
    elif k == "eq":
        body.append(D.equation(b[2], eq_no[b[1]]))
    elif k == "ref_list":
        for n, key in enumerate(cite_order, 1):
            tabs = '<w:tabs><w:tab w:val="left" w:pos="540"/></w:tabs>'
            body.append(f'<w:p>{D.ppr(jc="left", line=276, after=60, left=540, hanging=540, extra=tabs)}{D.run(f"[{n}]" + chr(9), sz=22)}{D.inline(refs.REFS[key], sz=22)}</w:p>')
    else:
        raise ValueError(k)

missing = [x for x in cite_order if x not in refs.REFS]
assert not missing, f"unknown references: {missing}"

# ------------------------------------------------------------------ table of contents (a real field: right-click > Update field in Word refreshes it)
SECT = ('<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="709" w:right="746" w:bottom="709" w:left="993" w:header="708" w:footer="708" w:gutter="0"/>'
        '<w:pgBorders w:offsetFrom="page"><w:top w:val="single" w:sz="4" w:space="24" w:color="auto"/><w:left w:val="single" w:sz="4" w:space="24" w:color="auto"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="24" w:color="auto"/><w:right w:val="single" w:sz="4" w:space="24" w:color="auto"/></w:pgBorders>')


def page_of(bm):
    return str(PAGES.get(bm, "0"))


toc_xml = []
for n, (lvl, text, bm) in enumerate(toc):
    pre = ""
    if n == 0:
        pre = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>')
    sz = 24 if lvl == 1 else 22
    label = text
    link = (f'<w:hyperlink w:anchor="{bm}" w:history="1">{D.run(label, sz=sz, b=(lvl == 1))}{D.run(chr(9), sz=sz)}'
            f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGEREF {bm} \\h </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            f'{D.run(page_of(bm), sz=sz, b=(lvl == 1))}<w:r><w:fldChar w:fldCharType="end"/></w:r></w:hyperlink>')
    post = ""
    if n == len(toc) - 1:
        post = f'<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    toc_xml.append(f'<w:p><w:pPr><w:pStyle w:val="TOC{lvl}"/></w:pPr>{pre}{link}{post}</w:p>')
section_break = f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/><w:sectPr>{SECT}<w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr></w:pPr></w:p>'

# ------------------------------------------------------------------ assemble the document
z = zipfile.ZipFile(TEMPLATE)
doc = z.read("word/document.xml").decode("utf8")
start = doc.index("<w:body>") + len("<w:body>")
toc_title_end = doc.index("</w:p>", doc.index("TABLE OF CONTENTS")) + len("</w:p>")
front = doc[start:toc_title_end]
# The template reaches the contents page through a run of empty paragraphs, so a longer title on the page before moves the heading. A page break puts it back.
ts = front.rfind("<w:p ", 0, front.index("TABLE OF CONTENTS"))
while True:
    prev = front.rfind("<w:p ", 0, ts)
    seg = front[prev:ts]
    text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", seg))
    if prev > 0 and seg.endswith("</w:p>") and not text.strip() and not any(t in seg for t in ("w:drawing", "sectPr", "<w:br", "w:pict")):
        front, ts = front[:prev] + front[ts:], prev
    else:
        break
head_end = front.index("<w:pPr>", ts) + len("<w:pPr>")
front = front[:head_end] + '<w:pageBreakBefore/><w:spacing w:before="1000" w:after="200"/>' + front[head_end:]
front = front.replace("&lt;&lt;PROJECT TITLE&gt;&gt;", D.esc(TITLE_CAPS)).replace("&lt;&lt;Project Title&gt;&gt;", D.esc(TITLE))
assert "titled _____." in front
front = front.replace("titled _____.", "titled " + D.esc(TITLE) + ".")
STUDENTS = [("Arijit Dutta", "12023002028077"), ("Aritra Panda", "12023002028078"), ("Ashmita Basak", "12023002028088"),
            ("Aritra Mandal", "12023002028080"), ("Ariyan Bhattacharjee", "12023002028081")]
# the template splits "<<Student_3 Name>>" over three runs; put it in the first and empty the others
m3 = re.search(r"<w:t>&lt;&lt;Student</w:t>((?:(?!<w:t[ >]).)*)<w:t>_3</w:t>((?:(?!<w:t[ >]).)*)<w:t[^>]*> Name&gt;&gt;</w:t>", front, flags=re.S)
assert m3
front = front.replace(m3.group(0), "<w:t>&lt;&lt;Student_3 Name&gt;&gt;</w:t>" + m3.group(1) + "<w:t></w:t>" + m3.group(2) + "<w:t></w:t>", 1)
for n, (nm, en) in enumerate(STUDENTS, 1):
    # cover page: name run, then the enrollment number split across runs ("No. XXXXXXXX" + "X" in the first entry)
    m = re.search(r"<w:p[ >](?:(?!</w:p>).)*?&lt;&lt;Student_%d Name&gt;&gt;.*?</w:p>" % n, front, flags=re.S)
    para = m.group(0).replace("&lt;&lt;Student_%d Name&gt;&gt;" % n, D.esc(nm))
    para = para.replace("<w:t>X</w:t>", "<w:t></w:t>")
    first, rest = para.split("<w:tab/>", 1)  # the template lines the numbers up with 8 default tabs; use one tab and a fixed stop
    para = (first + "<w:tab/>" + rest.replace("<w:tab/>", "")).replace("<w:pPr>", '<w:pPr><w:tabs><w:tab w:val="left" w:pos="5040"/></w:tabs>', 1)
    para = re.sub(r"X{8,9}", en, para)
    front = front.replace(m.group(0), para)
for n, (nm, en) in enumerate(STUDENTS, 1):
    # certificate: the name (its closing brackets may sit in the next run) and the registration number
    front = front.replace("&lt;&lt;Student Name_%d&gt;&gt;" % n, D.esc(nm) + " ")
    front = front.replace("&lt;&lt;Student Name_%d</w:t>" % n, D.esc(nm) + " </w:t>")
    front = re.sub(r"(<w:t[^>]*>)&gt;&gt;(\()?", lambda mm: mm.group(1) + (mm.group(2) or ""), front, count=1) if n > 1 else front
    front = front.replace(". XXXXXXXXX", ". " + en, 1)
front = front.replace(" of XXXX - XXXX", " of 2023 - 2027")
assert "Student" not in "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", front)) and "XXXXXXXXX" not in front.replace("XXXXXXXXXXXX", "")
final_sect = f'<w:sectPr><w:footerReference w:type="default" r:id="rId199"/><w:type w:val="nextPage"/>{SECT}<w:pgNumType w:start="1"/><w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr>'
new_doc = doc[:start] + front + "".join(toc_xml) + section_break + "".join(body) + final_sect + "</w:body></w:document>"
head = new_doc[:new_doc.index("<w:body>")]
if "xmlns:pic=" not in head:
    pass  # pic and a: namespaces are declared on the elements that use them

img_rels = "".join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}"/>' for rid, name, _ in media.values())
rels_xml = z.read("word/_rels/document.xml.rels").decode("utf8").replace(
    "</Relationships>", img_rels + '<Relationship Id="rId199" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>')
ctypes = z.read("[Content_Types].xml").decode("utf8").replace(
    "</Types>", '<Default Extension="jpg" ContentType="image/jpeg"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
styles = z.read("word/styles.xml").decode("utf8")
styles = styles.replace("</w:styles>", D.STYLES + "</w:styles>")
numbering = z.read("word/numbering.xml").decode("utf8")
first_num = numbering.index("<w:num ")
numbering = numbering[:first_num] + D.NUMBERING + numbering[first_num:]
numbering = numbering.replace("</w:numbering>", D.num_instances(lists[0] + 1) + "</w:numbering>")
core = z.read("docProps/core.xml").decode("utf8")
core = re.sub(r"<dc:title>.*?</dc:title>|<dc:title/>", "", core).replace("</cp:coreProperties>", f"<dc:title>{D.esc(TITLE)}</dc:title></cp:coreProperties>")

replaced = {"word/document.xml": new_doc, "word/_rels/document.xml.rels": rels_xml, "[Content_Types].xml": ctypes, "word/styles.xml": styles, "word/numbering.xml": numbering, "docProps/core.xml": core}
OUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as out:
    out.writestr("[Content_Types].xml", ctypes)
    for item in z.infolist():
        if item.filename == "[Content_Types].xml" or item.filename.endswith("/"):
            continue
        out.writestr(item.filename, replaced.get(item.filename, z.read(item.filename)))
    out.writestr("word/footer1.xml", D.FOOTER)
    for _, name, path in media.values():
        out.writestr(f"word/media/{name}", Path(path).read_bytes())

(HERE / "toc.json").write_text(json.dumps([{"level": l, "text": t, "bookmark": b} for l, t, b in toc], indent=1), encoding="utf8")
words = sum(len(re.sub(r"<[^>]+>", " ", x).split()) for x in body)
print(f"wrote {OUT.name}: {len(toc)} contents entries, {nf} figures, {nt} tables, {ne} equations, {len(cite_order)} references, about {words} words in the body")

"""Small helpers that write WordprocessingML (and Office Math) as strings. Used by build_report.py only."""

import re
import struct

FONT = "Times New Roman"
TEXT_W = 10167  # usable text width in twips (A4 minus the template's margins)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- runs and paragraphs

def rpr(sz=24, b=False, i=False, font=FONT, sup=False, sub=False, caps=False, smallcaps=False, hl=None, color=None):
    x = f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}" w:eastAsia="{font}"/>'
    if b:
        x += "<w:b/><w:bCs/>"
    if i:
        x += "<w:i/><w:iCs/>"
    if caps:
        x += "<w:caps/>"
    if smallcaps:
        x += "<w:smallCaps/>"
    if color:
        x += f'<w:color w:val="{color}"/>'
    x += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    if hl:
        x += f'<w:highlight w:val="{hl}"/>'
    if sup:
        x += '<w:vertAlign w:val="superscript"/>'
    if sub:
        x += '<w:vertAlign w:val="subscript"/>'
    return f"<w:rPr>{x}</w:rPr>"


def run(text, **kw):
    parts = text.split("\t")
    out = ""
    for n, part in enumerate(parts):
        if n:
            out += f"<w:r>{rpr(**kw)}<w:tab/></w:r>"
        if part:
            out += f'<w:r>{rpr(**kw)}<w:t xml:space="preserve">{esc(part)}</w:t></w:r>'
    return out


INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|`.+?`|\^\{.+?\}|_\{.+?\})")


def inline(text, sz=24, b=False, i=False, hl=None):
    """**bold**, *italic*, `code`, ^{sup}, _{sub} inside running text."""
    out = ""
    for tok in INLINE.split(text):
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
            out += run(tok[2:-2], sz=sz, b=True, i=i, hl=hl)
        elif tok.startswith("`") and tok.endswith("`"):
            out += run(tok[1:-1], sz=sz - 2, font="Courier New", b=b, hl=hl)
        elif tok.startswith("^{"):
            out += run(tok[2:-1], sz=sz, b=b, i=i, sup=True, hl=hl)
        elif tok.startswith("_{"):
            out += run(tok[2:-1], sz=sz, b=b, i=i, sub=True, hl=hl)
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            out += run(tok[1:-1], sz=sz, b=b, i=True, hl=hl)
        else:
            out += run(tok, sz=sz, b=b, i=i, hl=hl)
    return out


def ppr(jc="both", line=360, before=0, after=60, first=None, left=None, hanging=None, keep_next=False, keep_lines=False, style=None, extra="", page_break_before=False):
    x = ""
    if style:
        x += f'<w:pStyle w:val="{style}"/>'
    if keep_next:
        x += "<w:keepNext/>"
    if keep_lines:
        x += "<w:keepLines/>"
    if page_break_before:
        x += "<w:pageBreakBefore/>"
    x += extra
    x += f'<w:spacing w:before="{before}" w:after="{after}" w:line="{line}" w:lineRule="auto"/>'
    if first is not None or left is not None or hanging is not None:
        a = ""
        if left is not None:
            a += f' w:left="{left}"'
        if first is not None:
            a += f' w:firstLine="{first}"'
        if hanging is not None:
            a += f' w:hanging="{hanging}"'
        x += f"<w:ind{a}/>"
    x += f'<w:jc w:val="{jc}"/>'
    return f"<w:pPr>{x}</w:pPr>"


def para(text, sz=24, jc="both", b=False, i=False, hl=None, **kw):
    return f"<w:p>{ppr(jc=jc, **kw)}{inline(text, sz=sz, b=b, i=i, hl=hl)}</w:p>"


_bm = [100]


def heading(level, text, bm):
    """Heading 1/2/3 with a bookmark for the table of contents."""
    _bm[0] += 1
    n = _bm[0]
    sz = {1: 32, 2: 26, 3: 24}[level]
    return (f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/></w:pPr><w:bookmarkStart w:id="{n}" w:name="{bm}"/>'
            f'{run(text, sz=sz, b=True, i=(level == 3))}<w:bookmarkEnd w:id="{n}"/></w:p>')


# ---------------------------------------------------------------- lists

def bullets(items, num_id=20, sz=24):
    out = ""
    for it in items:
        out += (f'<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/></w:numPr>'
                f'<w:spacing w:before="0" w:after="40" w:line="360" w:lineRule="auto"/><w:ind w:left="720" w:hanging="360"/><w:jc w:val="both"/></w:pPr>{inline(it, sz=sz)}</w:p>')
    return out


def numbered(items, num_id, sz=24):
    out = ""
    for it in items:
        out += (f'<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/></w:numPr>'
                f'<w:spacing w:before="0" w:after="40" w:line="360" w:lineRule="auto"/><w:ind w:left="720" w:hanging="360"/><w:jc w:val="both"/></w:pPr>{inline(it, sz=sz)}</w:p>')
    return out


# ---------------------------------------------------------------- tables

def table(header, rows, widths, sz=20, align=None, shade_first_col=False):
    """Bordered table. widths in twips; align: per column 'left'|'center'|'right'."""
    total = sum(widths)
    align = align or ["left"] * len(widths)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    borders = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="000000"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    x = (f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{borders}</w:tblBorders>'
         '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="30" w:type="dxa"/><w:left w:w="80" w:type="dxa"/><w:bottom w:w="30" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>'
         f"<w:tblGrid>{grid}</w:tblGrid>")

    def cell(text, w, jc, head=False, first=False, keep=False):
        fill = '<w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/>' if head else ('<w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/>' if first and shade_first_col else "")
        paras = "".join(f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="{"center" if head else jc}"/></w:pPr>{inline(t, sz=sz, b=head)}</w:p>' for t in str(text).split("\n"))
        return f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{fill}<w:vAlign w:val="center"/></w:tcPr>{paras}</w:tc>'

    x += '<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>' + "".join(cell(h, w, "center", head=True) for h, w in zip(header, widths)) + "</w:tr>"
    for ri, r in enumerate(rows):
        x += "<w:tr><w:trPr><w:cantSplit/></w:trPr>" + "".join(cell(c, w, a, first=(n == 0), keep=(ri == 0)) for n, (c, w, a) in enumerate(zip(r, widths, align))) + "</w:tr>"
    x += "</w:tbl>"
    return x + '<w:p><w:pPr><w:spacing w:before="0" w:after="120" w:line="240" w:lineRule="auto"/></w:pPr></w:p>'


def roman(n):
    out = ""
    for v, s in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += s
            n -= v
    return out


def table_caption(n, title):
    """IEEE: 'TABLE I' then the title in small caps, both centred, above the table."""
    return (f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="160" w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>{run("TABLE " + roman(n), sz=20)}</w:p>'
            f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="0" w:after="80" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>{run(title, sz=20, smallcaps=True)}</w:p>')


def figure_caption(n, text):
    """IEEE: 'Fig. 1.' then the caption, below the figure. Short captions are centred, long ones justified."""
    jc = "center" if len(text) < 95 else "both"
    return (f'<w:p><w:pPr><w:spacing w:before="40" w:after="200" w:line="240" w:lineRule="auto"/><w:ind w:left="360" w:right="360"/><w:jc w:val="{jc}"/></w:pPr>'
            f'{run(f"Fig. {n}.", sz=20)}{run(" ", sz=20)}{inline(text, sz=20)}</w:p>')


# ---------------------------------------------------------------- images

def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", head[16:24])
    from PIL import Image
    with Image.open(path) as im:
        return im.size


_img = [0]


def image_para(rid, path, width_in, alt):
    _img[0] += 1
    w, h = png_size(path)
    cx = int(width_in * 914400)
    cy = int(cx * h / w)
    n = _img[0]
    return ('<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
            f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{500 + n}" name="Picture {n}" descr="{esc(alt)}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="{500 + n}" name="Picture {n}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
            '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


def placeholder(text, height=3600):
    """A visible, highlighted box for a figure that comes from the Colab notebook and has not been supplied yet."""
    border = "".join(f'<w:{s} w:val="dashed" w:sz="8" w:space="0" w:color="BF8F00"/>' for s in ("top", "left", "bottom", "right"))
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_W - 1200}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{border}</w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr>'
            f'<w:tblGrid><w:gridCol w:w="{TEXT_W - 1200}"/></w:tblGrid><w:tr><w:trPr><w:cantSplit/><w:trHeight w:val="{height}" w:hRule="atLeast"/></w:trPr>'
            f'<w:tc><w:tcPr><w:tcW w:w="{TEXT_W - 1200}" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="FFF2CC"/><w:vAlign w:val="center"/></w:tcPr>'
            f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>{run(text, sz=22, i=True)}</w:p></w:tc></w:tr></w:tbl>')


# ---------------------------------------------------------------- equations (a small LaTeX-like subset -> Office Math)

GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "Delta": "Δ", "epsilon": "ε", "varepsilon": "ε", "eta": "η", "theta": "θ", "lambda": "λ", "mu": "μ", "phi": "φ", "varphi": "φ",
         "rho": "ρ", "sigma": "σ", "tau": "τ", "psi": "ψ", "omega": "ω"}
SYMBOLS = {"cdot": "·", "times": "×", "le": "≤", "ge": "≥", "approx": "≈", "neq": "≠", "in": "∈", "cap": "∩", "pm": "±", "to": "→", "infty": "∞", "rightarrow": "→", "ell": "ℓ"}
FUNCS = {"ln", "exp", "min", "max", "arcsin", "sin", "cos", "log", "round", "argmax"}
MFONT = '<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'


def mrun(t, plain=False):
    p = '<m:rPr><m:sty m:val="p"/></m:rPr>' if plain else ""
    return f'<m:r>{p}{MFONT}<m:t xml:space="preserve">{esc(t)}</m:t></m:r>'


class _Math:
    def __init__(self, s):
        self.s, self.i = s, 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else ""

    def group(self):
        """{...} -> xml; or a single atom."""
        while self.peek() == " ":
            self.i += 1
        if self.peek() == "{":
            self.i += 1
            x = self.seq("}")
            self.i += 1
            return x
        return self.atom()

    def cmd(self):
        j = self.i + 1
        while j < len(self.s) and self.s[j].isalpha():
            j += 1
        name = self.s[self.i + 1:j]
        self.i = j
        return name

    def atom(self):
        c = self.peek()
        if c == "\\":
            name = self.cmd()
            if name == "frac":
                a, b = self.group(), self.group()
                return f"<m:f><m:num>{a}</m:num><m:den>{b}</m:den></m:f>"
            if name == "sqrt":
                a = self.group()
                return f"<m:rad><m:radPr><m:degHide m:val=\"1\"/></m:radPr><m:deg/><m:e>{a}</m:e></m:rad>"
            if name in ("text", "mathrm"):
                return mrun(self.raw_group(), plain=True)
            if name in ("sum", "prod"):
                lo = hi = ""
                while self.peek() in ("_", "^"):
                    op = self.peek()
                    self.i += 1
                    g = self.group()
                    lo, hi = (g, hi) if op == "_" else (lo, g)
                body = self.group()
                chr_ = "∑" if name == "sum" else "∏"
                hide = ("" if lo else '<m:subHide m:val="1"/>') + ("" if hi else '<m:supHide m:val="1"/>')
                return f'<m:nary><m:naryPr><m:chr m:val="{chr_}"/><m:limLoc m:val="undOvr"/>{hide}</m:naryPr><m:sub>{lo}</m:sub><m:sup>{hi}</m:sup><m:e>{body}</m:e></m:nary>'
            if name == "left":
                beg = self.s[self.i]
                self.i += 1
                inner = self.seq_until_right()
                end = self.s[self.i]
                self.i += 1
                b = "" if beg == "." else beg
                e = "" if end == "." else end
                return f'<m:d><m:dPr><m:begChr m:val="{b}"/><m:endChr m:val="{e}"/></m:dPr><m:e>{inner}</m:e></m:d>'
            if name == "cases":
                self.i += 1  # {
                rows, cur = [], ""
                depth = 0
                start = self.i
                while True:
                    c2 = self.s[self.i]
                    if c2 == "{":
                        depth += 1
                    elif c2 == "}":
                        if depth == 0:
                            break
                        depth -= 1
                    self.i += 1
                body = self.s[start:self.i]
                self.i += 1
                rows = [r for r in body.split("@@") if r.strip()]
                es = "".join(f"<m:e>{_Math(r).seq()}</m:e>" for r in rows)
                return f'<m:d><m:dPr><m:begChr m:val="{{"/><m:endChr m:val=""/></m:dPr><m:e><m:eqArr>{es}</m:eqArr></m:e></m:d>'
            if name in GREEK:
                return mrun(GREEK[name])
            if name in SYMBOLS:
                return mrun(SYMBOLS[name], plain=True)
            if name in FUNCS:
                return mrun(name, plain=True)
            raise ValueError("unknown command \\" + name + " in " + self.s)
        self.i += 1
        if c in "+-=<>(),.:;|/!%[]":
            return mrun(c, plain=True)
        return mrun(c, plain=c.isdigit())

    def raw_group(self):
        assert self.peek() == "{", self.s
        j = self.s.index("}", self.i)
        t = self.s[self.i + 1:j]
        self.i = j + 1
        return t

    def seq_until_right(self):
        out = ""
        while True:
            if self.s.startswith("\\right", self.i):
                self.i += 6
                return out
            out += self.term()

    def term(self):
        c = self.peek()
        if c == " ":
            self.i += 1
            return mrun(" ", plain=True) if False else ""
        base = self.atom()
        while self.peek() in ("_", "^"):
            subx = supx = None
            while self.peek() in ("_", "^"):
                op = self.peek()
                self.i += 1
                g = self.group()
                if op == "_":
                    subx = g
                else:
                    supx = g
            if subx is not None and supx is not None:
                base = f"<m:sSubSup><m:e>{base}</m:e><m:sub>{subx}</m:sub><m:sup>{supx}</m:sup></m:sSubSup>"
            elif subx is not None:
                base = f"<m:sSub><m:e>{base}</m:e><m:sub>{subx}</m:sub></m:sSub>"
            else:
                base = f"<m:sSup><m:e>{base}</m:e><m:sup>{supx}</m:sup></m:sSup>"
        return base

    def seq(self, stop=""):
        out = ""
        while self.i < len(self.s) and self.peek() != stop:
            out += self.term()
        return out


def omml(s):
    return _Math(s).seq()


def equation(s, n):
    """Display equation centred, number (n) at the right margin, built as a borderless three-column table."""
    w = [700, TEXT_W - 1400, 700]
    nb = "".join(f'<w:{x} w:val="nil"/>' for x in ("top", "left", "bottom", "right", "insideH", "insideV"))
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:tblBorders>{nb}</w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr>'
            f'<w:tblGrid><w:gridCol w:w="{w[0]}"/><w:gridCol w:w="{w[1]}"/><w:gridCol w:w="{w[2]}"/></w:tblGrid><w:tr><w:trPr><w:cantSplit/></w:trPr>'
            f'<w:tc><w:tcPr><w:tcW w:w="{w[0]}" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr></w:p></w:tc>'
            f'<w:tc><w:tcPr><w:tcW w:w="{w[1]}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:keepLines/><w:spacing w:before="60" w:after="60" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>'
            f"<m:oMathPara><m:oMathParaPr><m:jc m:val=\"center\"/></m:oMathParaPr><m:oMath>{omml(s)}</m:oMath></m:oMathPara></w:p></w:tc>"
            f'<w:tc><w:tcPr><w:tcW w:w="{w[2]}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="right"/></w:pPr>{run(f"({n})", sz=24)}</w:p></w:tc>'
            "</w:tr></w:tbl>")


# ---------------------------------------------------------------- styles, numbering, footer

STYLES = f"""
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/>
<w:pPr><w:keepNext/><w:keepLines/><w:pageBreakBefore/><w:spacing w:before="0" w:after="320" w:line="276" w:lineRule="auto"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/></w:pPr>
<w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" w:eastAsia="{FONT}"/><w:b/><w:bCs/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:unhideWhenUsed/><w:qFormat/>
<w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="280" w:after="120" w:line="276" w:lineRule="auto"/><w:jc w:val="left"/><w:outlineLvl w:val="1"/></w:pPr>
<w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" w:eastAsia="{FONT}"/><w:b/><w:bCs/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:unhideWhenUsed/><w:qFormat/>
<w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="200" w:after="80" w:line="276" w:lineRule="auto"/><w:jc w:val="left"/><w:outlineLvl w:val="2"/></w:pPr>
<w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" w:eastAsia="{FONT}"/><w:b/><w:bCs/><w:i/><w:iCs/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TOC1"><w:name w:val="toc 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/>
<w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9900"/></w:tabs><w:spacing w:before="100" w:after="20" w:line="240" w:lineRule="auto"/></w:pPr>
<w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/><w:b/><w:bCs/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TOC2"><w:name w:val="toc 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/>
<w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9900"/></w:tabs><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="480"/></w:pPr>
<w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:uiPriority w:val="99"/><w:unhideWhenUsed/></w:style>
"""

NUMBERING = """
<w:abstractNum w:abstractNumId="90"><w:multiLevelType w:val="hybridMultilevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="&#8226;"/><w:lvlJc w:val="left"/>
<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/></w:rPr></w:lvl></w:abstractNum>
<w:abstractNum w:abstractNumId="91"><w:multiLevelType w:val="hybridMultilevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/><w:lvlJc w:val="left"/>
<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/></w:rPr></w:lvl></w:abstractNum>
"""


def num_instances(n_lists):
    x = '<w:num w:numId="20"><w:abstractNumId w:val="90"/></w:num>'
    for k in range(n_lists):
        x += f'<w:num w:numId="{21 + k}"><w:abstractNumId w:val="91"/><w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>'
    return x


FOOTER = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/><w:jc w:val="center"/></w:pPr><w:r>{rpr(sz=22)}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{rpr(sz=22)}<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
          f'<w:r>{rpr(sz=22)}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{rpr(sz=22)}<w:t>1</w:t></w:r><w:r>{rpr(sz=22)}<w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')

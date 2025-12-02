#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: Richard Sitányi (richard@cdbox.sk)
File: greps.py
Version: 1.0
Date: 12/02/2025
"""


import sys
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path

try:
    import scribus
except ImportError:
    print("This script must be run from inside Scribus.")
    sys.exit(1)

# =============================================================================
# UNICODE NORMALIZATION
# =============================================================================

import unicodedata

def normalize_input(text, is_pattern):
    # Converts tags like <NBSP>, <EMSPACE> and Unicode codes \uXXXX to real Unicode.

    if not text:
        return text

    # 1) TAGS
    TAGS = {
        # Base
        "<SPACE>": "\u0020",
        "<TAB>": "\u0009",
        "<NBSP>": "\u00a0",
        "<NARROW_NBSP>": "\u202f",
        "<ENSPACE>": "\u2002",
        "<EMSPACE>": "\u2003",
        "<THREE_PER_EM_SPACE>": "\u2004",
        "<FOUR_PER_EM_SPACE>": "\u2005",
        "<SIX_PER_EM_SPACE>": "\u2006",
        "<FIGURESPACE>": "\u2007",
        "<PUNCTSPACE>": "\u2008",
        "<THINSPACE>": "\u2009",
        "<HAIRSPACE>": "\u200a",
        "<ZEROSPACE>": "\u200b",
        "<ENDPARA>": "\u000d",
        "<LINEBREAK>": "\u2028",
        "<COLUMNBREAK>": "\u001a",
        "<FRAMEBREAK>": "\u001b",

        # Dashes
        "<EMDASH>": "\u2014",
        "<ENDASH>": "\u2013",
        "<NON_BREAKING_HYPHEN>": "\u2011",

        # Symbols
        "<BULLET>": "\u2022",
        "<BACKSLASH>": "\\",
        "<CARET>": "^",
        "<COPYRIGHT>": "\u00A9",
        "<ELLIPSIS>": "\u2026",
        "<REGTM>": "\u00AE",
        "<TRADEMARK>": "\u2122",
        "<LEFTPARENTHESIS>": "\(",
        "<RIGHTPARENTHESIS>": "\)",
        "<LEFT_SQUARE_BRACKET>": "\[",
        "<RIGHT_SQUARE_BRACKET>": "\]",
        "<LEFT_CURLY_BRACKET>": "\{",
        "<RIGHT_CURLY_BRACKET>": "\}",
    }

    for tag, uni in TAGS.items():
        if tag in text:
            text = text.replace(tag, uni)

    # 2) FOUND – only for REPLACEMENT
    if not is_pattern:
        FOUND_TAGS = {
            "<FOUND1>": r"\g<1>",
            "<FOUND2>": r"\g<2>",
            "<FOUND3>": r"\g<3>",
            "<FOUND4>": r"\g<4>",
            "<FOUND5>": r"\g<5>",
            "<FOUND6>": r"\g<6>",
            "<FOUND7>": r"\g<7>",
            "<FOUND8>": r"\g<8>",
            "<FOUND9>": r"\g<9>",
        }
        for tag, rep in FOUND_TAGS.items():
            if tag in text:
                text = text.replace(tag, rep)

    # 3) Unicode codes \uXXXX, \xXX, \UXXXXXXXX
    text = re.sub(r"\\u([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r"\\x([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r"\\U([0-9A-Fa-f]{8})", lambda m: chr(int(m.group(1), 16)), text)

    # 4) Unicode by name \N{NAME}
    text = re.sub(r"\\N\{([^}]+)\}", lambda m: unicodedata.lookup(m.group(1)), text)

    # 5) Special escapes
    if not is_pattern:
        text = text.replace("\\t", "\t")
        text = text.replace("\\n", "\n")
        text = text.replace("\\r", "\r")

    return text


# =============================================================================
# MESSAGEBOX HELPERS
# =============================================================================

def tk_info(parent, title, message):
    messagebox.showinfo(title, message, parent=parent)

def tk_warning(parent, title, message):
    messagebox.showwarning(title, message, parent=parent)

def tk_confirm(parent, title, message):
    return messagebox.askokcancel(title, message, parent=parent)


# =============================================================================
# REQUIRE OPEN DOCUMENT
# =============================================================================

if scribus.haveDoc() == 0:
    tk_warning(None, "Warning", "You should open at least one document.")
    sys.exit(1)


# =============================================================================
# JSON PATHS
# =============================================================================

QUERIES_DIR = Path(__file__).parent / "queries"
QUERIES_PATH = QUERIES_DIR / "queries.json"


# =============================================================================
# JSON HANDLERS
# =============================================================================

def get_all_queries_from_json():
    if QUERIES_PATH.exists():
        try:
            with open(QUERIES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_all_queries_to_json(data):
    QUERIES_DIR.mkdir(exist_ok=True)
    with open(QUERIES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_all_query_names():
    data = get_all_queries_from_json()
    names = [k for k,v in data.items() if not k.startswith("_") and isinstance(v,list) and len(v)==2]
    names.append("[Custom]")
    return names


# =============================================================================
# HISTORY
# =============================================================================

def load_histories():
    data = get_all_queries_from_json()
    fw_hist = data.get("_find_what_history", [])
    cht_hist = data.get("_change_to_history", [])
    return (fw_hist if isinstance(fw_hist, list) else []), \
           (cht_hist if isinstance(cht_hist, list) else [])

def get_all_finds_what():
    fw_hist, _ = load_histories()
    return fw_hist

def get_all_changes_to():
    _, cht_hist = load_histories()
    return cht_hist

def update_history(key, value):
    data = get_all_queries_from_json()
    lst = data.get(key, [])
    if not isinstance(lst, list):
        lst = []
    value = value.strip()
    if value:
        if value in lst:
            lst.remove(value)
        lst.insert(0, value)
    data[key] = lst[:10]
    save_all_queries_to_json(data)


# =============================================================================
# DETECTION HELPERS
# =============================================================================

def has_story_selected():
    try:
        scribus.getTextLength()
        return True
    except:
        pass
    try:
        if scribus.selectionCount()==1:
            obj = scribus.getSelectedObject(0)
            return scribus.getObjectType(obj)=="TextFrame"
    except:
        pass
    return False

def get_story_roots_for_document():
    try:
        objs = scribus.getAllObjects()
    except:
        return []
    roots=[]
    for o in objs:
        try:
            if scribus.getObjectType(o)!="TextFrame":
                continue
        except:
            continue
        try:
            prev = scribus.getPrevLinkedFrame(o)
        except:
            prev=None
        if not prev:
            roots.append(o)
    return roots

def get_current_story_root():
    try:
        if scribus.selectionCount()>=1:
            obj = scribus.getSelectedObject(0)
            if scribus.getObjectType(obj)=="TextFrame":
                try:
                    root = scribus.getFirstLinkedFrame(obj)
                    return root if root else obj
                except:
                    return obj
    except:
        pass
    roots = get_story_roots_for_document()
    return roots[0] if roots else None


# =============================================================================
# GUI MAIN
# =============================================================================

def get_values(parent=None):

    dialog = tk.Toplevel(parent)
    dialog.title("Greps")
    dialog.geometry("500x400")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.attributes("-topmost", True)

    # ============================================================
    # QUERY COMBO
    # ============================================================
    ttk.Label(dialog, text="Query:").place(x=20,y=20)
    q = tk.StringVar()
    queryCombo = ttk.Combobox(dialog, width=60, state="readonly", textvariable=q, values=get_all_query_names())
    queryCombo.place(x=80,y=20)
    queryCombo.current(len(get_all_query_names())-1)

    # ============================================================
    # FIND & CHANGE FIELDS
    # ============================================================
    ttk.Label(dialog, text="Find what:").place(x=20,y=100)
    fw = tk.StringVar()
    find_whatCombo = ttk.Combobox(dialog, width=40, textvariable=fw, values=get_all_finds_what())
    find_whatCombo.place(x=20,y=120)

    ttk.Label(dialog, text="Change to:").place(x=20,y=160)
    cht = tk.StringVar()
    change_toCombo = ttk.Combobox(dialog, width=40, textvariable=cht, values=get_all_changes_to())
    change_toCombo.place(x=20,y=180)

    # ============================================
    # SPECIAL CHARACTER MENUS
    # ============================================

    # MENU FOR FW
    fw_menu_btn = tk.Menubutton(dialog, text="Special characters for search", relief="raised")
    fw_menu = tk.Menu(fw_menu_btn, tearoff=0)
    fw_menu_btn.config(menu=fw_menu)
    fw_menu_btn.place(x=300, y=118)

    # MENU FOR CHT
    cht_menu_btn = tk.Menubutton(dialog, text="Special characters for replace", relief="raised")
    cht_menu = tk.Menu(cht_menu_btn, tearoff=0)
    cht_menu_btn.config(menu=cht_menu)
    cht_menu_btn.place(x=300, y=178)

    # ------------------------------------------------
    # TOP LEVEL: Tab / Line break / End of paragraph
    # ------------------------------------------------
    fw_menu.add_command(label="Tab", command=lambda: insert_into_fw("<TAB>"))
    fw_menu.add_command(label="Line break", command=lambda: insert_into_fw("<LINEBREAK>"))
    fw_menu.add_command(label="End of paragraph", command=lambda: insert_into_fw("<ENDPARA>"))
    fw_menu.add_separator()

    cht_menu.add_command(label="Tab", command=lambda: insert_into_cht("<TAB>"))
    cht_menu.add_command(label="Line break", command=lambda: insert_into_cht("<LINEBREAK>"))
    cht_menu.add_command(label="End of paragraph", command=lambda: insert_into_cht("<ENDPARA>"))
    cht_menu.add_separator()

    # ------------------------------------------------
    # SYMBOLS
    # ------------------------------------------------
    symbols_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="Symbols", menu=symbols_fw)

    symbols_cht = tk.Menu(cht_menu, tearoff=0)
    cht_menu.add_cascade(label="Symbols", menu=symbols_cht)

    symbols_fw_lst = [
        ("Bullet •", "<BULLET>"),
        ("Backslash \\", "<BACKSLASH>"),
        ("Caret ^", "<CARET>"),
        ("Copyright ©", "<COPYRIGHT>"),
        ("Ellipsis …", "<ELLIPSIS>"),
        ("Registered trademark ®", "<REGTM>"),
        ("Trademark ™", "<TRADEMARK>"),
    ]

    symbols_cht_lst = [
        ("Bullet •", "<BULLET>"),
        ("Caret ^", "<CARET>"),
        ("Copyright ©", "<COPYRIGHT>"),
        ("Ellipsis …", "<ELLIPSIS>"),
        ("Registered trademark ®", "<REGTM>"),
        ("Trademark ™", "<TRADEMARK>"),
    ]

    for label, tag in symbols_fw_lst:
        symbols_fw.add_command(label=label, command=lambda t=tag: insert_into_fw(t))
    for label, tag in symbols_cht_lst:
        symbols_cht.add_command(label=label, command=lambda t=tag: insert_into_cht(t))

    # ------------------------------------------------
    # PARENTHESES AND BRACKETS
    # ------------------------------------------------
    pab_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="Parentheses and brackets", menu=pab_fw)

    pab_fw_lst = [
        ("Left parenthesis (", "<LEFTPARENTHESIS>"),
        ("Right parenthesis )", "<RIGHTPARENTHESIS>"),
        ("Left square bracket [", "<LEFT_SQUARE_BRACKET>"),
        ("Right square bracket ]", "<RIGHT_SQUARE_BRACKET>"),
        ("Left curly bracket {", "<LEFT_CURLY_BRACKET>"),
        ("Right curly bracket }", "<RIGHT_CURLY_BRACKET>"),
    ]

    for label, tag in pab_fw_lst:
        pab_fw.add_command(label=label, command=lambda t=tag: insert_into_fw(t))

    # ------------------------------------------------
    # DASHES NAD HYPHENS
    # ------------------------------------------------
    dashes_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="Dashes and hyphens", menu=dashes_fw)

    dashes_cht = tk.Menu(cht_menu, tearoff=0)
    cht_menu.add_cascade(label="Dashes and hyphens", menu=dashes_cht)

    dashes_fw.add_command(label="Em dash —", command=lambda: insert_into_fw("<EMDASH>"))
    dashes_fw.add_command(label="En dash –", command=lambda: insert_into_fw("<ENDASH>"))
    dashes_fw.add_command(label="Non-breaking hyphen ‑", command=lambda: insert_into_fw("<NON_BREAKING_HYPHEN>"))

    dashes_cht.add_command(label="Em dash —", command=lambda: insert_into_cht("<EMDASH>"))
    dashes_cht.add_command(label="En dash –", command=lambda: insert_into_cht("<ENDASH>"))
    dashes_cht.add_command(label="Non-breaking hyphen ‑", command=lambda: insert_into_cht("<NON_BREAKING_HYPHEN>"))

    # ------------------------------------------------
    # WHITE SPACES
    # ------------------------------------------------
    ws_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="White spaces", menu=ws_fw)

    ws_cht = tk.Menu(cht_menu, tearoff=0)
    cht_menu.add_cascade(label="White spaces", menu=ws_cht)

    white_spaces = [
        ("Normal space", "<SPACE>"),
        ("Em space", "<EMSPACE>"),
        ("En space", "<ENSPACE>"),
        ("No break space", "<NBSP>"),
        ("Narrow no break space", "<NARROW_NBSP>"),
        ("Hair space", "<HAIRSPACE>"),
        ("Thin space", "<THINSPACE>"),
        ("Three per em space", "<THREE_PER_EM_SPACE>"),
        ("Four per em space", "<FOUR_PER_EM_SPACE>"),
        ("Six per em space", "<SIX_PER_EM_SPACE>"),
        ("Zero width space", "<ZEROSPACE>"),
        ("Figure space", "<FIGURESPACE>"),
        ("Punctuation space", "<PUNCTSPACE>"),
    ]

    for label, tag in white_spaces:
        ws_fw.add_command(label=label, command=lambda t=tag: insert_into_fw(t))
        ws_cht.add_command(label=label, command=lambda t=tag: insert_into_cht(t))

    # ------------------------------------------------
    # QUOTATION MARKS
    # ------------------------------------------------
    quotes_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="Quotation marks", menu=quotes_fw)

    quotes_fw.add_command(label="Any double quotation marks", command=lambda: insert_into_fw(r"[\"“”«»„‟]"))
    quotes_fw.add_command(label="Any single quotation marks", command=lambda: insert_into_fw(r"[\'‘’‹›‚‛]"))
    quotes_fw.add_separator()
    quotes_fw.add_command(label="Straight double quotation mark", command=lambda: insert_into_fw("\""))
    quotes_fw.add_command(label="Double left quotation mark", command=lambda: insert_into_fw("“"))
    quotes_fw.add_command(label="Double right quotation mark", command=lambda: insert_into_fw("”"))
    quotes_fw.add_command(label="Double left-pointing angle quotation mark", command=lambda: insert_into_fw("«"))
    quotes_fw.add_command(label="Double right-pointing angle quotation mark", command=lambda: insert_into_fw("»"))
    quotes_fw.add_command(label="Double low-9 quotation mark", command=lambda: insert_into_fw("„"))
    quotes_fw.add_command(label="Double high-reversed-9 quotation mark", command=lambda: insert_into_fw("‟"))
    quotes_fw.add_separator()
    quotes_fw.add_command(label="Straight single quotation mark", command=lambda: insert_into_fw("'"))
    quotes_fw.add_command(label="Single left quotation mark", command=lambda: insert_into_fw("‘"))
    quotes_fw.add_command(label="Single right quotation mark", command=lambda: insert_into_fw("’"))
    quotes_fw.add_command(label="Single left-pointing angle quotation mark", command=lambda: insert_into_fw("‹"))
    quotes_fw.add_command(label="Single right-pointing angle quotation mark", command=lambda: insert_into_fw("›"))
    quotes_fw.add_command(label="Single low-9 quotation mark", command=lambda: insert_into_fw("‚"))
    quotes_fw.add_command(label="Single high-reversed-9 quotation mark", command=lambda: insert_into_fw("‛"))

    quotes_cht = tk.Menu(cht_menu, tearoff=0)
    cht_menu.add_cascade(label="Quotation marks", menu=quotes_cht)
    quotes_cht.add_command(label="Straight double quotation mark", command=lambda: insert_into_cht("\""))
    quotes_cht.add_command(label="Double left quotation mark", command=lambda: insert_into_cht("“"))
    quotes_cht.add_command(label="Double right quotation mark", command=lambda: insert_into_cht("”"))
    quotes_cht.add_command(label="Double left-pointing angle quotation mark", command=lambda: insert_into_cht("«"))
    quotes_cht.add_command(label="Double right-pointing angle quotation mark", command=lambda: insert_into_cht("»"))
    quotes_cht.add_command(label="Double low-9 quotation mark", command=lambda: insert_into_cht("„"))
    quotes_cht.add_command(label="Double high-reversed-9 quotation mark", command=lambda: insert_into_cht("‟"))
    quotes_cht.add_separator()
    quotes_cht.add_command(label="Straight single quotation mark", command=lambda: insert_into_cht("'"))
    quotes_cht.add_command(label="Single left quotation mark", command=lambda: insert_into_cht("‘"))
    quotes_cht.add_command(label="Single right quotation mark", command=lambda: insert_into_cht("’"))
    quotes_cht.add_command(label="Single left-pointing angle quotation mark", command=lambda: insert_into_cht("‹"))
    quotes_cht.add_command(label="Single right-pointing angle quotation mark", command=lambda: insert_into_cht("›"))
    quotes_cht.add_command(label="Single low-9 quotation mark", command=lambda: insert_into_cht("‚"))
    quotes_cht.add_command(label="Single high-reversed-9 quotation mark", command=lambda: insert_into_cht("‛"))

    # ------------------------------------------------
    # BREAK CHARACTERS
    # ------------------------------------------------
    br_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="Break characters", menu=br_fw)
    br_fw.add_command(label="Line break", command=lambda: insert_into_fw("<LINEBREAK>"))
    br_fw.add_command(label="End of paragraph", command=lambda: insert_into_fw("<ENDPARA>"))
    br_fw.add_command(label="Column break", command=lambda: insert_into_fw("<COLUMNBREAK>"))
    br_fw.add_command(label="Frame break", command=lambda: insert_into_fw("<FRAMEBREAK>"))

    br_cht = tk.Menu(cht_menu, tearoff=0)
    cht_menu.add_cascade(label="Break characters", menu=br_cht)
    br_cht.add_command(label="Line break", command=lambda: insert_into_cht("<LINEBREAK>"))
    br_cht.add_command(label="End of paragraph", command=lambda: insert_into_cht("<ENDPARA>"))
    br_cht.add_command(label="Column break", command=lambda: insert_into_cht("<COLUMNBREAK>"))
    br_cht.add_command(label="Frame break", command=lambda: insert_into_cht("<FRAMEBREAK>"))

    # ------------------------------------------------
    # UNICODE CHARACTERS
    # ------------------------------------------------
    unich_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="Unicode characters", menu=unich_fw)
    unich_fw.add_command(label="\\xXX", command=lambda: insert_into_fw(r"\x<PUT CODE HERE>"))
    unich_fw.add_command(label="\\uXXXX", command=lambda: insert_into_fw(r"\u<PUT CODE HERE>"))
    unich_fw.add_command(label="\\UXXXXXXXX", command=lambda: insert_into_fw(r"\U<PUT CODE HERE>"))
    unich_fw.add_command(label="\\N{NAME}", command=lambda: insert_into_fw(r"\N{<PUT NAME HERE>}"))

    unich_cht = tk.Menu(cht_menu, tearoff=0)
    cht_menu.add_cascade(label="Unicode characters", menu=unich_cht)
    unich_cht.add_command(label="\\xXX", command=lambda: insert_into_cht(r"\x<PUT CODE HERE>"))
    unich_cht.add_command(label="\\uXXXX", command=lambda: insert_into_cht(r"\u<PUT CODE HERE>"))
    unich_cht.add_command(label="\\UXXXXXXXX", command=lambda: insert_into_cht(r"\U<PUT CODE HERE>"))
    unich_cht.add_command(label="\\N{NAME}", command=lambda: insert_into_cht(r"\N{<PUT NAME HERE>}"))

    # ------------------------------------------------
    # WILDCARDS
    # ------------------------------------------------
    wild_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="Wildcards", menu=wild_fw)
    wild_fw.add_command(label="Any character", command=lambda: insert_into_fw(r"."))
    wild_fw.add_command(label="Any digit", command=lambda: insert_into_fw(r"\d"))
    wild_fw.add_command(label="Any white space", command=lambda: insert_into_fw(r"\s"))
    wild_fw.add_command(label="Any word character", command=lambda: insert_into_fw(r"\w"))
    wild_fw.add_separator()
    wild_fw.add_command(label="No digit", command=lambda: insert_into_fw(r"\D"))
    wild_fw.add_command(label="No white space", command=lambda: insert_into_fw(r"\S"))
    wild_fw.add_command(label="No word character", command=lambda: insert_into_fw(r"\W"))

    # ------------------------------------------------
    # LOCATIONS
    # ------------------------------------------------
    loc_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="Locations", menu=loc_fw)
    loc_fw.add_command(label="Beginning of word", command=lambda: insert_into_fw(r"\b<PUT PATTERN HERE>"))
    loc_fw.add_command(label="End of word", command=lambda: insert_into_fw(r"<PUT PATTERN HERE>\b"))
    loc_fw.add_command(label="Word boundary", command=lambda: insert_into_fw(r"\b<PUT PATTERN HERE>\b"))
    loc_fw.add_separator()
    loc_fw.add_command(label="Beginning of paragraph", command=lambda: insert_into_fw(r"^<PUT PATTERN HERE>"))
    loc_fw.add_command(label="End of paragraph", command=lambda: insert_into_fw(r"<PUT PATTERN HERE>$"))

    # ------------------------------------------------
    # REPETITIONS
    # ------------------------------------------------
    rep_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="Repetitions", menu=rep_fw)
    rep_fw.add_command(label="Zero or one time", command=lambda: insert_into_fw(r"<PUT PATTERN HERE>?"))
    rep_fw.add_command(label="Zero or more times", command=lambda: insert_into_fw(r"<PUT PATTERN HERE>*"))
    rep_fw.add_command(label="One or more times", command=lambda: insert_into_fw(r"<PUT PATTERN HERE>+"))
    rep_fw.add_separator()
    rep_fw.add_command(label="Zero or one time (shortest match)", command=lambda: insert_into_fw(r"<PUT PATTERN HERE>??"))
    rep_fw.add_command(label="Zero or more times (shortest match)", command=lambda: insert_into_fw(r"<PUT PATTERN HERE>*?"))
    rep_fw.add_command(label="One or more times (shortest match)", command=lambda: insert_into_fw(r"<PUT PATTERN HERE>+?"))

    # ------------------------------------------------
    # MATCHES
    # ------------------------------------------------
    match_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="Matches", menu=match_fw)
    match_fw.add_command(label="Capturing group", command=lambda: insert_into_fw(r"()"))
    match_fw.add_command(label="Non-capturing group", command=lambda: insert_into_fw(r"(?:)"))
    match_fw.add_command(label="Character set", command=lambda: insert_into_fw(r"[]"))
    match_fw.add_command(label="Or", command=lambda: insert_into_fw(r"|"))
    match_fw.add_separator()
    match_fw.add_command(label="Positive lookbehind assertion", command=lambda: insert_into_fw(r"(?<=)"))
    match_fw.add_command(label="Negative lookbehind assertion", command=lambda: insert_into_fw(r"(?<!)"))
    match_fw.add_command(label="Positive lookahead assertion", command=lambda: insert_into_fw(r"(?=)"))
    match_fw.add_command(label="Negative lookahead assertion", command=lambda: insert_into_fw(r"(?!)"))

    # ------------------------------------------------
    # MODIFIERS
    # ------------------------------------------------
    mod_fw = tk.Menu(fw_menu, tearoff=0)
    fw_menu.add_cascade(label="Modifiers", menu=mod_fw)
    mod_fw.add_command(label="Case-insensitive ON", command=lambda: insert_into_fw(r"(?i)"))
    mod_fw.add_command(label="Case-insensitive OFF", command=lambda: insert_into_fw(r"(?!i)"))
    mod_fw.add_command(label="ASCII-only matching ON", command=lambda: insert_into_fw(r"(?a)"))
    mod_fw.add_command(label="ASCII-only matching OFF", command=lambda: insert_into_fw(r"(?!a)"))

    # ------------------------------------------------
    # FOUND
    # ------------------------------------------------
    found_cht = tk.Menu(cht_menu, tearoff=0)
    cht_menu.add_cascade(label="Found", menu=found_cht)
    for i in range(1, 10):
        found_cht.add_command(label=f"Found {i}", command=lambda i=i: insert_into_cht(f"<FOUND{i}>"))

    def insert_into_fw(value):
        current = fw.get()
        fw.set(current + value)

    def insert_into_cht(value):
        current = cht.get()
        cht.set(current + value)


    # ============================================================
    # SEARCH COMBO
    # ============================================================
    def compute_search_items():
        items=[]
        items.append("Document")
        if has_story_selected():
            items.append("Story")
        return items

    ttk.Label(dialog, text="Search:").place(x=20,y=220)

    searchCombo = ttk.Combobox(dialog, width=20, state="readonly", values=compute_search_items())
    searchCombo.place(x=20, y=240)
    if searchCombo["values"]:
        searchCombo.current(0)

    def refresh_search_items(event=None):
        vals = compute_search_items()
        cur = searchCombo.get()
        searchCombo["values"] = vals
        if cur in vals:
            searchCombo.set(cur)
        elif vals:
            searchCombo.current(0)

    searchCombo.bind("<Button-1>", refresh_search_items)
    searchCombo.bind("<FocusIn>", refresh_search_items)

    # ============================================================
    # SEARCH STATE
    # ============================================================
    search_state = {
        "mode": None,
        "pattern": None,
        "regex": None,
        "frames": [],
        "story_index": 0,
        "char_index": 0,
        "found_count": 0,
        "story_text_cache": {},
    }

    def search_state_reset():
        search_state["mode"]=None
        search_state["pattern"]=None
        search_state["regex"]=None
        search_state["frames"]=[]
        search_state["story_index"]=0
        search_state["char_index"]=0
        search_state["found_count"]=0
        search_state["story_text_cache"] = {}

    def init_search_state_if_needed():
        pattern_raw = fw.get()
        pattern = normalize_input(pattern_raw, is_pattern=True)
        mode = searchCombo.get() or "Document"

        if search_state["mode"]!=mode or search_state["pattern"]!=pattern:
            search_state_reset()
            search_state["mode"]=mode
            search_state["pattern"]=pattern

        if search_state["frames"]:
            return

        # Build frames list
        if mode=="Story":
            root = get_current_story_root()
            frames=[root] if root else []

        else:  # Document (Scribus supports only current document anyway)
            frames = get_story_roots_for_document()

        search_state["frames"] = frames
        search_state["story_index"]=0
        search_state["char_index"]=0

    # ============================================================
    # BUTTONS + STATES
    # ============================================================

    def update_buttons_state(found=False):
        fw_t = fw.get()
        cht_t = cht.get()

        if fw_t=="" and cht_t=="":
            find_next_btn.state(["disabled"])
            change_btn.state(["disabled"])
            change_all_btn.state(["disabled"])
            change_find_btn.state(["disabled"])
            return

        if fw_t=="" and cht_t!="":
            find_next_btn.state(["disabled"])
            change_btn.state(["disabled"])
            change_all_btn.state(["disabled"])
            change_find_btn.state(["disabled"])
            return

        if fw_t != "" and cht_t == "" and not found:
            find_next_btn.state(["!disabled"])
            change_btn.state(["disabled"])
            change_all_btn.state(["!disabled"])
            change_find_btn.state(["disabled"])
            return

        if fw_t!="" and cht_t!="" and not found:
            find_next_btn.state(["!disabled"])
            change_btn.state(["disabled"])
            change_all_btn.state(["!disabled"])
            change_find_btn.state(["disabled"])
            return

        if found:
            find_next_btn.state(["!disabled"])
            change_btn.state(["!disabled"])
            change_all_btn.state(["!disabled"])
            change_find_btn.state(["!disabled"])

    # ============================================================
    # FIND NEXT
    # ============================================================

    def on_find_next():
        pattern_raw = fw.get()
        pattern = normalize_input(pattern_raw, is_pattern=True)
        if not pattern:
            search_state_reset()
            update_buttons_state(found=False)
            return

        # Compile regex
        try:
            if search_state["regex"] is None or search_state["pattern"] != pattern:
                rg = re.compile(pattern)
                search_state["regex"] = rg
                search_state["pattern"] = pattern
            else:
                rg = search_state["regex"]
        except re.error:
            tk_warning(dialog, "Regex", "Invalid regular expression.")
            search_state_reset()
            update_buttons_state(found=False)
            return

        # Initialization of frames / selection
        init_search_state_if_needed()
        frames = search_state["frames"]
        if not frames:
            update_buttons_state(found=False)
            return

        # So that we do not get stuck on selection
        try:
            scribus.setNormalMode()
            scribus.deselectAll()
        except:
            pass

        mode = search_state["mode"]

        while search_state["story_index"] < len(frames):

            frame = frames[search_state["story_index"]]

            # Snapshot of the text for this frame (entire story chain)
            if frame not in search_state["story_text_cache"]:
                try:
                    txt = scribus.getAllText(frame)
                except:
                    txt = ""
                search_state["story_text_cache"][frame] = txt

            full_text = search_state["story_text_cache"][frame]
            i = search_state["char_index"]

            match = None

            # =============================================================
            # DOCUMENT / STORY MODE
            # =============================================================
            m = rg.search(full_text, i)
            if m:
                gstart = m.start()
                gend   = m.end()
                match = True
            else:
                match = None

            # ========== FOUND ==========
            if match:
                length = gend - gstart
                if length <= 0:
                    # Safety catch – skip to the next story
                    search_state["story_index"] += 1
                    search_state["char_index"] = 0
                    continue

                try:
                    scribus.selectObject(frame)
                    scribus.setEditMode()
                    scribus.selectText(gstart, length)
                except:
                    pass

                # Index shift
                search_state["char_index"] = gend
                search_state["found_count"] += 1

                update_history("_find_what_history", fw.get())
                update_history("_change_to_history", cht.get())
                find_whatCombo["values"] = get_all_finds_what()
                change_toCombo["values"] = get_all_changes_to()

                update_buttons_state(found=True)
                dialog.lift()
                dialog.attributes("-topmost", True)
                dialog.focus_force()
                return

            # ========== NOTHING IN THIS STORY → next ==========
            search_state["story_index"] += 1
            search_state["char_index"] = 0

        # ========== END OF ALL STORIES ==========
        cnt = search_state["found_count"]
        tk_info(dialog, "Find next", f"Found {cnt} match(es).")
        dialog.lift()
        search_state_reset()
        update_buttons_state(found=False)


    # ============================================================
    # CHANGE
    # ============================================================

    def on_change():
        # Replace the currently found match and keep the replacement selected.
        pattern_raw = fw.get()
        pattern = normalize_input(pattern_raw, is_pattern=True)
        replacement_raw = cht.get()
        replacement = normalize_input(replacement_raw, is_pattern=False)

        if not pattern:
            return

        # Regex – same as for Find next
        rg = search_state.get("regex")
        if rg is None or search_state.get("pattern") != pattern:
            try:
                rg = re.compile(pattern)
                search_state["regex"] = rg
                search_state["pattern"] = pattern
            except re.error:
                tk_warning(dialog, "Regex error", "Invalid regular expression.")
                return

        # Must be a valid frame and story index
        if not search_state["frames"]:
            tk_warning(dialog, "Change", "No active match. Use Find next first.")
            return

        idx = search_state["story_index"]
        if idx < 0 or idx >= len(search_state["frames"]):
            tk_warning(dialog, "Change", "No active match. Use Find next first.")
            return

        frame = search_state["frames"][idx]

        # Text story from cache or reloaded
        full_text = search_state["story_text_cache"].get(frame)
        if full_text is None:
            try:
                full_text = scribus.getAllText(frame)
            except:
                full_text = ""
            search_state["story_text_cache"][frame] = full_text

        if not full_text:
            tk_warning(dialog, "Change", "No text in current story.")
            return

        gend = search_state.get("char_index", 0)
        if not isinstance(gend, int) or gend <= 0:
            tk_warning(dialog, "Change", "No active match to replace.")
            return

        if gend > len(full_text):
            gend = len(full_text)

        # Find a match that ends with gend
        matches = list(rg.finditer(full_text))
        last_match = None
        for m in matches:
            if m.end() == gend:
                last_match = m
                break

        if last_match is None:
            tk_warning(dialog, "Change", "No active match to replace.")
            return

        gstart = last_match.start()
        old_end = last_match.end()
        old_len = old_end - gstart

        try:
            new_text = last_match.expand(replacement)
        except Exception as e:
            tk_warning(dialog, "Error", f"Replacement failed:\n{e}")
            return

        # Updating text cache
        new_full_text = full_text[:gstart] + new_text + full_text[old_end:]
        search_state["story_text_cache"][frame] = new_full_text

        try:
            scribus.selectObject(frame)

            scribus.setEditMode()
            scribus.selectText(gstart, old_len, frame)

            scribus.setNormalMode()
            scribus.setEditMode()
            scribus.deleteText()

            scribus.insertText(new_text, gstart, frame)

            scribus.selectText(gstart, len(new_text), frame)

        except Exception as e:
            tk_warning(dialog, "Scribus Error", str(e))
            return

        search_state["char_index"] = gstart + len(new_text)

        update_buttons_state(found=False)
        dialog.lift()
        dialog.focus_force()


    def on_change_all():
        # Replace ALL matches in Story or Document.
        pattern_raw = fw.get()
        pattern = normalize_input(pattern_raw, is_pattern=True)
        replacement_raw = cht.get()
        replacement = normalize_input(replacement_raw, is_pattern=False)

        if not pattern:
            return

        # If we already have a search running, we will use its mode, otherwise the mode from the combo box.
        effective_mode = search_state["mode"] or (searchCombo.get() or "Document")

        frames = []

        if search_state["mode"] == effective_mode and search_state["frames"]:
            frames = list(search_state["frames"])
        else:
            if effective_mode == "Story":
                root = get_current_story_root()
                if root:
                    frames = [root]
            else:
                frames = get_story_roots_for_document()

        if not frames:
            tk_info(dialog, "Change all", "No story to process.")
            return

        try:
            scribus.setNormalMode()
            scribus.deselectAll()
        except:
            pass

        try:
            rg = re.compile(pattern)
        except re.error:
            tk_warning(dialog, "Regex error", "Invalid regular expression.")
            return

        total_replaced = 0

        for frame in frames:
            try:
                full_text = scribus.getAllText(frame)
            except:
                full_text = ""

            if not full_text:
                continue

            # Function for sub with match.expand() support
            def repl(m):
                nonlocal total_replaced
                total_replaced += 1
                return m.expand(replacement)

            new_full = rg.sub(repl, full_text)

            try:
                scribus.selectObject(frame)
                scribus.setEditMode()
                scribus.setText(new_full, frame)
                scribus.layoutTextChain(frame)
            except:
                pass

        try:
            scribus.setNormalMode()
            scribus.deselectAll()
        except:
            pass

        tk_info(dialog, "Change all", f"Replaced {total_replaced} match(es).")

        search_state_reset()
        update_buttons_state(found=False)

        dialog.lift()
        dialog.focus_force()


    def on_change_find():
        # Change one match and immediately search for the next one.
        pattern_raw = fw.get()
        pattern = normalize_input(pattern_raw, is_pattern=True)
        replacement_raw = cht.get()
        replacement = normalize_input(replacement_raw, is_pattern=False)

        if not pattern:
            return

        rg = search_state.get("regex")
        if rg is None or search_state.get("pattern") != pattern:
            try:
                rg = re.compile(pattern)
                search_state["regex"] = rg
                search_state["pattern"] = pattern
            except re.error:
                tk_warning(dialog, "Regex error", "Invalid regular expression.")
                return

        if not search_state["frames"]:
            tk_warning(dialog, "Change/Find", "No active match. Use Find next first.")
            return

        idx = search_state["story_index"]
        if idx < 0 or idx >= len(search_state["frames"]):
            tk_warning(dialog, "Change/Find", "No active match. Use Find next first.")
            return

        frame = search_state["frames"][idx]

        full_text = search_state["story_text_cache"].get(frame)
        if full_text is None:
            try:
                full_text = scribus.getAllText(frame)
            except:
                full_text = ""
            search_state["story_text_cache"][frame] = full_text

        if not full_text:
            tk_warning(dialog, "Change/Find", "No text in current story.")
            return

        gend = search_state.get("char_index", 0)
        if not isinstance(gend, int) or gend <= 0:
            tk_warning(dialog, "Change/Find", "No active match to replace.")
            return

        if gend > len(full_text):
            gend = len(full_text)

        matches = list(rg.finditer(full_text))
        last_match = None
        for m in matches:
            if m.end() == gend:
                last_match = m
                break

        if last_match is None:
            tk_warning(dialog, "Change/Find", "No active match to replace.")
            return

        gstart = last_match.start()
        old_end = last_match.end()
        old_len = old_end - gstart

        try:
            new_text = last_match.expand(replacement)
        except Exception as e:
            tk_warning(dialog, "Error", f"Replacement failed:\n{e}")
            return

        new_full_text = full_text[:gstart] + new_text + full_text[old_end:]
        search_state["story_text_cache"][frame] = new_full_text

        try:
            scribus.selectObject(frame)
            scribus.setEditMode()

            scribus.selectText(gstart, old_len, frame)

            scribus.deleteText()

            scribus.insertText(new_text, gstart, frame)

        except Exception as e:
            tk_warning(dialog, "Scribus Error", str(e))
            return

        search_state["char_index"] = gstart + len(new_text)

        # Reset selection so that Find next behaves correctly
        try:
            scribus.setNormalMode()
            scribus.deselectAll()
        except:
            pass

        mode = search_state.get("mode")

        while search_state["story_index"] < len(search_state["frames"]):

            frame = search_state["frames"][search_state["story_index"]]

            full_text = search_state["story_text_cache"].get(frame)
            if full_text is None:
                try:
                    full_text = scribus.getAllText(frame)
                except:
                    full_text = ""
                search_state["story_text_cache"][frame] = full_text

            txt = full_text
            i = search_state["char_index"]

            if i < 0 or i > len(txt):
                i = 0

            m = rg.search(txt, i)
            if m:
                gstart2 = m.start()
                gend2 = m.end()
                length2 = gend2 - gstart2

                try:
                    scribus.selectObject(frame)
                    scribus.setEditMode()
                    scribus.selectText(gstart2, length2, frame)
                except:
                    pass

                search_state["char_index"] = gend2
                search_state["found_count"] += 1

                update_buttons_state(found=True)
                dialog.lift()
                dialog.focus_force()
                return

            search_state["story_index"] += 1
            search_state["char_index"] = 0

        tk_info(dialog, "Find", f"Search completed. {search_state['found_count']} occurrence(s) found.")

        search_state_reset()
        update_buttons_state(found=False)
        dialog.lift()
        dialog.focus_force()


    # ============================================================
    # BUTTONS
    # ============================================================

    find_next_btn = ttk.Button(dialog, text="Find next", command=on_find_next)
    change_btn     = ttk.Button(dialog, text="Change", command=on_change)
    change_all_btn = ttk.Button(dialog, text="Change all", command=on_change_all)
    change_find_btn= ttk.Button(dialog, text="Change/Find", command=on_change_find)

    find_next_btn.place(x=20,y=280)
    change_btn.place(x=110,y=280)
    change_all_btn.place(x=200,y=280)
    change_find_btn.place(x=290,y=280)

    update_buttons_state(False)

    def fw_cht_changed(*args):
        search_state_reset()
        update_buttons_state(found=False)

    fw_change_id  = fw.trace_add("write", fw_cht_changed)
    cht_change_id = cht.trace_add("write", fw_cht_changed)


    # ============================================================
    # SAVE / DELETE QUERY
    # ============================================================

    delete_query_btn = ttk.Button(dialog, text="Delete query")

    def on_save_query():
        name = simpledialog.askstring("Save query", "Enter name:", parent=dialog)
        if not name:
            return
        data = get_all_queries_from_json()
        data[name] = [fw.get(), cht.get()]
        save_all_queries_to_json(data)

        update_history("_find_what_history", fw.get())
        update_history("_change_to_history", cht.get())

        find_whatCombo["values"] = get_all_finds_what()
        change_toCombo["values"] = get_all_changes_to()

        queryCombo["values"] = get_all_query_names()
        q.set(name)
        delete_query_btn.state(["!disabled"])
        tk_info(dialog, "Saved", f"Query <{name}> saved.")

    def on_delete_query():
        cur = q.get()
        if cur=="[Custom]":
            return
        data = get_all_queries_from_json()
        if cur not in data:
            return
        if not tk_confirm(dialog, "Delete","Delete this query?"):
            return
        del data[cur]
        save_all_queries_to_json(data)
        queryCombo["values"] = get_all_query_names()
        q.set("[Custom]")
        delete_query_btn.state(["disabled"])
        tk_info(dialog, "Deleted", f"Query <{cur}> deleted.")

    ttk.Button(dialog,text="Save query",command=on_save_query).place(x=20,y=60)
    delete_query_btn.config(command=on_delete_query)
    delete_query_btn.place(x=110,y=60)


    # ============================================================
    # COMBO SELECT HANDLING
    # ============================================================

    updating=False
    orig_fw=""
    orig_cht=""

    def update_from_query(*args):
        nonlocal updating, orig_fw, orig_cht
        data = get_all_queries_from_json()
        cur = q.get()

        if cur!="[Custom]":
            lst = data.get(cur)
            if lst and len(lst)==2:
                updating=True
                fw.set(lst[0])
                cht.set(lst[1])
                updating=False
                orig_fw=lst[0]
                orig_cht=lst[1]
            delete_query_btn.state(["!disabled"])
        else:
            delete_query_btn.state(["disabled"])
            orig_fw=fw.get()
            orig_cht=cht.get()

        search_state_reset()
        update_buttons_state(found=False)

    queryCombo.bind("<<ComboboxSelected>>", update_from_query)
    find_whatCombo.bind("<<ComboboxSelected>>", update_from_query)
    change_toCombo.bind("<<ComboboxSelected>>", update_from_query)

    def on_edit_custom(*args):
        nonlocal updating, orig_fw, orig_cht
        if updating:
            return
        if q.get()!="[Custom]":
            if fw.get()!=orig_fw or cht.get()!=orig_cht:
                q.set("[Custom]")
                delete_query_btn.state(["disabled"])

    fw_custom_id  = fw.trace_add("write", on_edit_custom)
    cht_custom_id = cht.trace_add("write", on_edit_custom)


    # ============================================================
    # CLOSE BUTTON
    # ============================================================

    def on_close():
        try:
            fw.trace_remove("write", fw_change_id)
            cht.trace_remove("write", cht_change_id)
            fw.trace_remove("write", fw_custom_id)
            cht.trace_remove("write", cht_custom_id)
        except:
            pass

        dialog.destroy()

    ttk.Button(dialog, text="Close", command=on_close).place(x=20,y=350)
    dialog.protocol("WM_DELETE_WINDOW", on_close)

    dialog.wait_window()


# =============================================================================
# MAIN
# =============================================================================

def main(argv):
    if not QUERIES_PATH.exists():
        tk_warning(None, "Missing file", f"{QUERIES_PATH} not found.\nCreating new one.")
        save_all_queries_to_json({})
    root=tk.Tk()
    root.withdraw()
    get_values(root)

def main_wrapper(argv):
    try:
        scribus.statusMessage("Running script...")
        scribus.progressReset()
        main(argv)
    finally:
        if scribus.haveDoc():
            scribus.setRedraw(True)
            scribus.redrawAll()
        scribus.statusMessage("Script finished.")
        scribus.progressReset()

if __name__=="__main__":
    main_wrapper(sys.argv)

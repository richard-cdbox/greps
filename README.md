# greps
Regular Expressions for Scribus

_A full-featured Find/Change engine inspired by Adobe InDesign GREP_

---

**Author:** Richard Sitányi (richard@cdbox.sk)

**File:** greps.py

**Version:** 1.0

**Date:** 12/02/2025

---

## Overview

**GREPS** is an advanced Find/Change dialog for Scribus, bringing a powerful **regular expression engine**, Unicode support, reusable queries, and an intuitive UI modeled after **Adobe InDesign GREP** search.

It is designed to overcome the limitations of Scribus’ built-in Search/Replace and provide professional-grade text processing directly inside Scribus documents.

## Key Features

### Full Regular Expression Support

Powered by Python’s **re** engine:

* searching in **current Story** or **entire Document**
* supports lookahead / lookbehind
* supports capturing groups and replacements
* supports unicode-aware character classes

### 4 Types of Unicode Input Supported

You can mix them freely:

|Syntax|Example|Meaning|
|:-----|:------|:------|
|\xXX|\x20|2-digit hex|
|\uXXXX|\u0020|4-digit Unicode|
|\UXXXXXXXX|\U0001F600|8-digit Unicode|
|\N{NAME}|\N{EN SPACE}|Unicode by name|
|**TAGS**|\<NBSP\>, \<EMSPACE\>, \<ENDPARA\>|Custom shortcuts|

All are normalized automatically by **normalize\_input()**.

Custom **TAGS** greatly simplify writing patterns and are especially useful for whitespace, breaks, and special characters.

## Powerful Custom Search/Replace UI

### Special Character Menus

Extensive style menu for both **search field** and **replace field**:

* White spaces (normal, thin, hair, em/en, NBSP, etc.)
* Hyphens and dashes
* Quotation marks (straight, smart, angle quotes…)
* Symbols (bullet, copyright, trademark…)
* Parentheses & brackets
* Break characters (line/column/frame break, end of paragraph)
* Unicode insertion helpers
* Wildcards
* Locations (word boundaries, beginning/end of paragraph…)
* Repetitions (\*, \+, ?, lazy quantifiers)
* Matches (groups, non-capturing, lookaheads/lookbehinds)
* Modifiers ((?i), (?a))
* Found groups (\<FOUND1\> … \<FOUND9\>) for replacement

### Query System

* Save and load your own GREP queries
* Query history for both search and replace fields
* A special [Custom] entry is used when modifying an existing or creating own query

### Fully Scripted GREP Workflow

Buttons:

* **Find next**
* **Change**
* **Change all**
* **Change/Find**

## Scribus-Specific Notes

### Line Break and End of Paragraph ARE NOT \n

Scribus internally uses special characters:

|Meaning|TAG|Unicode|
|:------|:--|:------|
|End of paragraph|\<ENDPARA\>|\u000D (CR)|
|Line break|\<LINEBREAK\>|\u2028|
|Column break|\<COLUMNBREAK\>|\u001A|
|Frame break|\<FRAMEBREAK\>|\u001B|

### Because of this:

* ^ and $ match **start/end of entire text**, not each paragraph
* (?m) multiline flag **does NOT behave like should be**
* . does **NOT** match across paragraphs
* Patterns expecting **\n** for paragraph breaks will fail

This is not a bug:  
**Scribus does not use LF (\n) to represent paragraphs.**

Use TAGS instead:

* \<ENDPARA\>
* \<LINEBREAK\>
* etc.

## Behavior Notes

### Fully Unicode-Aware Regular Expressions

Python’s regex engine treats \w, \b, etc. as **Unicode-aware**, so:

* \bže\b works correctly
* diacritic letters behave as expected
* NBSP and exotic spaces are non-word characters

### Accurate Story / Document Processing

* Find/Change correctly handles linked frames
* No text loss or corruption
* Story-specific searches never overwrite the wrong story

### Replace supports capture groups

Use \<FOUND1\> … \<FOUND9\> in replacement field.

## Tested Scribus Versions

GREPS has been tested extensively on:

* **Scribus 1.6.4 (stable)**
* **Scribus 1.7.0 (development)**

All features work identically across both versions.

## Limitations

* ^ and $ match **start/end of entire text**, not each paragraph
* Multiline regex ((?m)) does not behave like should be due to Scribus '\\r' paragraphs
* DOTALL ((?s)) does not cross \<ENDPARA\> boundaries

## Saved Queries

Examples are provided in queries.json

## Installation

1. Place greps folder containing **greps.py** file and **queries** folder where you store your scripts.
2. Run script via _Script → Execute Script…_

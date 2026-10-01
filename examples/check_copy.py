"""Minimal end-to-end example: load a dictionary and check ad copy."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sensitive_words import Checker, Dictionary

dictionary = Dictionary.load(os.path.join(os.path.dirname(__file__), "dictionary.json"))
checker = Checker(dictionary)

fields = {
    "title": "Earn FREE MONEY​ today",
    "body": "Act now: wire\t \ntransfer required to secure your Ｇｕａｒａｎｔｅｅｄ bonus.",
    "cta": "Learn more",
}

hits = checker.check(fields)
for hit in hits:
    text = fields[hit.field]
    print(f"{hit.field}: rule={hit.rule_id} range=[{hit.start}, {hit.end}) "
          f"highlight={text[hit.start:hit.end]!r}")

if not hits:
    print("no sensitive words found")

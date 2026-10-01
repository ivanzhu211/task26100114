import json
import tempfile
import unittest
from pathlib import Path

from adcheck import Checker, Hit, MatchMode, Rule, load_dictionary
from adcheck.normalize import normalize

ZWSP = "\u200b"
BOM = "\ufeff"


def substring(rule_id, term):
    return Rule(rule_id, term, MatchMode.SUBSTRING)


def word(rule_id, term):
    return Rule(rule_id, term, MatchMode.WORD)


class NormalizeTest(unittest.TestCase):
    def test_fullwidth_and_casefold(self):
        self.assertEqual(normalize("ＡＢＣｘｙｚ").text, "abcxyz")

    def test_ideographic_space(self):
        self.assertEqual(normalize("a　b").text, "a b")

    def test_hidden_chars_removed(self):
        self.assertEqual(normalize(f"a{ZWSP}b{BOM}c").text, "abc")

    def test_whitespace_collapsed_not_stripped(self):
        self.assertEqual(normalize("  a\t \nb  ").text, " a b ")

    def test_casefold_expansion_shares_source(self):
        normalized = normalize("ß")
        self.assertEqual(normalized.text, "ss")
        self.assertEqual(normalized.sources, (frozenset({0}), frozenset({0})))


class RequiredScenarioTest(unittest.TestCase):
    def test_fullwidth_hidden_sharp_s(self):
        checker = Checker(
            [
                substring("r-as", "as"),
                substring("r-s", "s"),
                substring("r-ss-1", "ss"),
                substring("r-ss-2", "ＳＳ"),
            ]
        )
        hits = checker.check({"body": f"Ａ{ZWSP}ß"})
        self.assertIn(Hit("r-as", "body", 0, 3), hits)
        self.assertEqual(hits.count(Hit("r-s", "body", 2, 3)), 1)
        self.assertIn(Hit("r-ss-1", "body", 2, 3), hits)
        self.assertIn(Hit("r-ss-2", "body", 2, 3), hits)
        self.assertEqual(len(hits), 4)

    def test_whitespace_fold_hit(self):
        checker = Checker([substring("r-wire", "wire transfer required")])
        hits = checker.check({"body": "wire\t \ntransfer required"})
        self.assertEqual(hits, [Hit("r-wire", "body", 0, 24)])

    def test_hidden_chars_outside_hit_not_included(self):
        checker = Checker([substring("r-wire", "wire transfer required")])
        hits = checker.check({"body": f"{ZWSP}wire\t \ntransfer required{ZWSP}"})
        self.assertEqual(hits, [Hit("r-wire", "body", 1, 25)])


class MatchingBehaviorTest(unittest.TestCase):
    def test_overlapping_and_contained_hits(self):
        checker = Checker(
            [substring("r-aa", "aa"), substring("r-a", "a"), substring("r-aaa", "aaa")]
        )
        hits = checker.check({"f": "aaa"})
        self.assertEqual(
            sorted(hits, key=lambda h: (h.rule_id, h.start, h.end)),
            sorted(
                [
                    Hit("r-a", "f", 0, 1),
                    Hit("r-a", "f", 1, 2),
                    Hit("r-a", "f", 2, 3),
                    Hit("r-aa", "f", 0, 2),
                    Hit("r-aa", "f", 1, 3),
                    Hit("r-aaa", "f", 0, 3),
                ],
                key=lambda h: (h.rule_id, h.start, h.end),
            ),
        )

    def test_same_rule_same_range_reported_once(self):
        checker = Checker([substring("r-s", "s")])
        hits = checker.check({"f": "ß"})
        self.assertEqual(hits, [Hit("r-s", "f", 0, 1)])

    def test_word_mode_boundaries(self):
        checker = Checker([word("r-cat", "cat")])
        self.assertEqual(checker.check({"f": "cat"}), [Hit("r-cat", "f", 0, 3)])
        self.assertEqual(checker.check({"f": "scatter"}), [])
        self.assertEqual(checker.check({"f": "cat2"}), [])
        self.assertEqual(checker.check({"f": "cat_s"}), [])
        self.assertEqual(checker.check({"f": "cat,"}), [Hit("r-cat", "f", 0, 3)])
        self.assertEqual(checker.check({"f": "the cat."}), [Hit("r-cat", "f", 4, 7)])

    def test_word_mode_combining_mark_blocks(self):
        # U+0301 是 Mn 类别，属于词内字符。
        checker = Checker([word("r-cat", "cat")])
        self.assertEqual(checker.check({"f": "cat\u0301"}), [])

    def test_word_mode_substring_rule_unaffected(self):
        checker = Checker([substring("r-cat", "cat")])
        self.assertEqual(checker.check({"f": "scatter"}), [Hit("r-cat", "f", 1, 4)])

    def test_fields_never_joined(self):
        checker = Checker([substring("r-ab", "ab")])
        self.assertEqual(checker.check({"title": "xa", "body": "bx"}), [])

    def test_multiple_fields_report_field_name(self):
        checker = Checker([substring("r-x", "bad")])
        hits = checker.check({"title": "bad title", "body": "bad body", "cta": "ok"})
        self.assertEqual(
            hits, [Hit("r-x", "title", 0, 3), Hit("r-x", "body", 0, 3)]
        )

    def test_hidden_char_between_ends_included(self):
        checker = Checker([substring("r-ab", "ab")])
        hits = checker.check({"f": f"a{ZWSP}{BOM}b"})
        self.assertEqual(hits, [Hit("r-ab", "f", 0, 4)])

    def test_casefold_and_fullwidth_equivalence(self):
        checker = Checker([substring("r-ss", "ss")])
        self.assertEqual(checker.check({"f": "ＳＳ"}), [Hit("r-ss", "f", 0, 2)])


class ReuseTest(unittest.TestCase):
    def test_results_not_affected_by_previous_checks(self):
        checker = Checker([substring("r-x", "bad")])
        first = checker.check({"f": "bad"})
        second = checker.check({"f": "clean"})
        third = checker.check({"f": "bad"})
        self.assertEqual(first, [Hit("r-x", "f", 0, 3)])
        self.assertEqual(second, [])
        self.assertEqual(third, first)


class DictionaryTest(unittest.TestCase):
    def test_load_dictionary_and_check(self):
        entries = [
            {"id": "r1", "term": "as", "mode": "substring"},
            {"id": "r2", "term": "wire transfer", "mode": "word"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dict.json"
            path.write_text(json.dumps(entries), encoding="utf-8")
            rules = load_dictionary(path)
            checker = Checker.from_json(path)
        self.assertEqual(
            rules,
            [
                Rule("r1", "as", MatchMode.SUBSTRING),
                Rule("r2", "wire transfer", MatchMode.WORD),
            ],
        )
        hits = checker.check({"body": "wire  transfer now"})
        self.assertEqual(hits, [Hit("r2", "body", 0, 14)])

    def test_duplicate_rule_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dict.json"
            path.write_text(
                json.dumps(
                    [
                        {"id": "r1", "term": "a", "mode": "substring"},
                        {"id": "r1", "term": "b", "mode": "word"},
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_dictionary(path)


if __name__ == "__main__":
    unittest.main()

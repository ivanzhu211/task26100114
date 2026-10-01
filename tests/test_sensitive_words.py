import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sensitive_words import (
    SUBSTRING,
    WHOLE_WORD,
    Checker,
    Dictionary,
    Rule,
    normalize,
    normalize_term,
)


def make_checker(*rules):
    return Checker(Dictionary(list(rules)))


def triples(hits):
    return sorted((h.rule_id, h.field, h.start, h.end) for h in hits)


class NormalizerTest(unittest.TestCase):
    def test_fullwidth_and_casefold(self):
        self.assertEqual(normalize_term("Ｈｅｌｌｏ"), "hello")
        self.assertEqual(normalize_term("STRASSE"), "strasse")
        self.assertEqual(normalize_term("ß"), "ss")

    def test_ideographic_space_and_whitespace_collapse(self):
        self.assertEqual(normalize_term("a　b"), "a b")
        self.assertEqual(normalize_term("a\t \n\rb"), "a b")

    def test_hidden_chars_removed(self):
        self.assertEqual(normalize_term("a​b﻿c"), "abc")

    def test_no_stripping_of_edges(self):
        self.assertEqual(normalize_term("  a  "), " a ")

    def test_index_map_tracks_origins(self):
        n = normalize("Ａ​ß")
        self.assertEqual(n.text, "ass")
        self.assertEqual(n.index_map[0], frozenset({0}))
        self.assertEqual(n.index_map[1], frozenset({2}))
        self.assertEqual(n.index_map[2], frozenset({2}))

    def test_collapsed_whitespace_owns_all_participants(self):
        n = normalize("a\t \nb")
        self.assertEqual(n.text, "a b")
        self.assertEqual(n.index_map[1], frozenset({1, 2, 3}))


class DictionaryTest(unittest.TestCase):
    def test_load_from_json_file(self):
        payload = {
            "rules": [
                {"id": "r1", "term": "as", "mode": "substring"},
                {"id": "r2", "term": "wire transfer", "mode": "whole_word"},
            ]
        }
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as handle:
            json.dump(payload, handle)
            path = handle.name
        try:
            dictionary = Dictionary.load(path)
        finally:
            os.unlink(path)
        self.assertEqual([r.id for r in dictionary.rules], ["r1", "r2"])
        self.assertEqual(
            [p.normalized_term for p in dictionary.prepared],
            ["as", "wire transfer"],
        )

    def test_duplicate_rule_id_rejected(self):
        with self.assertRaises(ValueError):
            Dictionary(
                [
                    Rule(id="r1", term="a", mode=SUBSTRING),
                    Rule(id="r1", term="b", mode=SUBSTRING),
                ]
            )

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            Dictionary([Rule(id="r1", term="a", mode="regex")])

    def test_empty_normalized_term_rejected(self):
        with self.assertRaises(ValueError):
            Dictionary([Rule(id="r1", term="​", mode=SUBSTRING)])


class RequiredScenarioTest(unittest.TestCase):
    def test_fullwidth_hidden_casefold_expansion(self):
        checker = make_checker(
            Rule(id="as", term="as", mode=SUBSTRING),
            Rule(id="s", term="s", mode=SUBSTRING),
            Rule(id="ss-latin", term="ss", mode=SUBSTRING),
            Rule(id="ss-fullwidth", term="ＳＳ", mode=SUBSTRING),
        )
        hits = checker.check({"title": "Ａ​ß"})
        self.assertIn(("as", "title", 0, 3), triples(hits))
        self.assertEqual(
            [(h.start, h.end) for h in hits if h.rule_id == "s"], [(2, 3)]
        )
        self.assertIn(("ss-latin", "title", 2, 3), triples(hits))
        self.assertIn(("ss-fullwidth", "title", 2, 3), triples(hits))

    def test_whitespace_fold_highlight(self):
        checker = make_checker(
            Rule(id="wire", term="wire transfer required", mode=SUBSTRING)
        )
        hits = checker.check({"body": "wire\t \ntransfer required"})
        self.assertEqual(triples(hits), [("wire", "body", 0, 24)])

    def test_whitespace_fold_highlight_with_hidden_edges(self):
        checker = make_checker(
            Rule(id="wire", term="wire transfer required", mode=SUBSTRING)
        )
        hits = checker.check({"body": "​wire\t \ntransfer required​"})
        self.assertEqual(triples(hits), [("wire", "body", 1, 25)])


class MatchingTest(unittest.TestCase):
    def test_overlapping_and_contained_hits_all_reported(self):
        checker = make_checker(
            Rule(id="aa", term="aa", mode=SUBSTRING),
            Rule(id="aaa", term="aaa", mode=SUBSTRING),
            Rule(id="a", term="a", mode=SUBSTRING),
        )
        hits = checker.check({"body": "aaa"})
        self.assertEqual(
            triples(hits),
            [
                ("a", "body", 0, 1),
                ("a", "body", 1, 2),
                ("a", "body", 2, 3),
                ("aa", "body", 0, 2),
                ("aa", "body", 1, 3),
                ("aaa", "body", 0, 3),
            ],
        )

    def test_whole_word_boundaries(self):
        checker = make_checker(Rule(id="cat", term="cat", mode=WHOLE_WORD))
        self.assertEqual(triples(checker.check({"f": "cat"})), [("cat", "f", 0, 3)])
        self.assertEqual(
            triples(checker.check({"f": "the cat!"})), [("cat", "f", 4, 7)]
        )
        self.assertEqual(checker.check({"f": "concat"}), [])
        self.assertEqual(checker.check({"f": "cat2"}), [])
        self.assertEqual(checker.check({"f": "cat_"}), [])
        self.assertEqual(
            triples(checker.check({"f": "cat-"})), [("cat", "f", 0, 3)]
        )

    def test_whole_word_respects_marks_and_numbers(self):
        checker = make_checker(Rule(id="a", term="a", mode=WHOLE_WORD))
        self.assertEqual(checker.check({"f": "1a"}), [])
        self.assertEqual(checker.check({"f": "a1"}), [])
        self.assertEqual(checker.check({"f": "a\u0301"}), [])
        self.assertEqual(triples(checker.check({"f": "a"})), [("a", "f", 0, 1)])

    def test_fields_never_concatenated(self):
        checker = make_checker(Rule(id="ab", term="ab", mode=SUBSTRING))
        self.assertEqual(checker.check({"title": "xa", "cta": "by"}), [])

    def test_same_rule_same_range_reported_once(self):
        checker = make_checker(Rule(id="s", term="s", mode=SUBSTRING))
        hits = checker.check({"f": "ß"})
        self.assertEqual(triples(hits), [("s", "f", 0, 1)])

    def test_same_normalized_term_different_ids_both_reported(self):
        checker = make_checker(
            Rule(id="one", term="ss", mode=SUBSTRING),
            Rule(id="two", term="ＳＳ", mode=SUBSTRING),
        )
        hits = checker.check({"f": "ß"})
        self.assertEqual(
            triples(hits), [("one", "f", 0, 1), ("two", "f", 0, 1)]
        )

    def test_hidden_chars_between_ends_included(self):
        checker = make_checker(Rule(id="ab", term="ab", mode=SUBSTRING))
        hits = checker.check({"f": "a​﻿b"})
        self.assertEqual(triples(hits), [("ab", "f", 0, 4)])

    def test_hidden_chars_outside_ends_excluded(self):
        checker = make_checker(Rule(id="ab", term="ab", mode=SUBSTRING))
        hits = checker.check({"f": "​ab​"})
        self.assertEqual(triples(hits), [("ab", "f", 1, 3)])

    def test_multiple_fields_reported_independently(self):
        checker = make_checker(Rule(id="x", term="bad", mode=SUBSTRING))
        hits = checker.check({"title": "bad title", "body": "bad body", "cta": "ok"})
        self.assertEqual(
            triples(hits),
            [("x", "body", 0, 3), ("x", "title", 0, 3)],
        )

    def test_checker_is_stateless_across_calls(self):
        checker = make_checker(Rule(id="x", term="bad", mode=SUBSTRING))
        first = checker.check({"title": "bad"})
        second = checker.check({"title": "clean"})
        third = checker.check({"title": "bad"})
        self.assertEqual(triples(first), [("x", "title", 0, 3)])
        self.assertEqual(second, [])
        self.assertEqual(triples(third), triples(first))

    def test_dictionary_reusable_across_checkers(self):
        dictionary = Dictionary([Rule(id="x", term="bad", mode=SUBSTRING)])
        self.assertEqual(len(Checker(dictionary).check({"f": "bad"})), 1)
        self.assertEqual(len(Checker(dictionary).check({"f": "bad"})), 1)


if __name__ == "__main__":
    unittest.main()

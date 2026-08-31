from cpcr_git_builder.normalizers import normalize_answer, boxed, answer_equal
from cpcr_git_builder.routing import infer_category, route_category, sort_rows_cpcr
from cpcr_git_builder.glyph_codec import text_to_glyphs, glyphs_to_text, text_to_binary, binary_to_text


def test_normalize_answer():
    assert normalize_answer(r"$\\boxed{00042}$.") == "42"
    assert normalize_answer(" 6 / 8 ") == "3/4"
    assert normalize_answer("3.1400") == "3.14"
    assert boxed("007") == r"\boxed{7}"
    assert answer_equal(r"\boxed{01}", "1")


def test_cpcr_routing_order():
    rows = [
        {"prompt": "Compute 5 xor 3", "category": "bit_manipulation", "verified": False},
        {"prompt": "Convert binary 101 to decimal", "category": "numeral_system", "verified": True},
        {"prompt": "What is 7*12?", "category": "equation_numeric", "verified": True},
    ]
    out = sort_rows_cpcr(rows)
    assert [r["category"] for r in out] == ["numeral_system", "equation_numeric", "bit_manipulation"]
    assert out[-1]["train_allowed"] is False


def test_verified_bit_can_train_but_late():
    r = route_category("bit_manipulation", verified=True)
    assert r.stage == 3
    assert r.train_allowed is True


def test_category_inference():
    assert infer_category("Decrypt this Caesar cipher") == "cipher"
    assert infer_category("Convert binary 1010 to decimal") == "numeral_system"
    assert infer_category("Compute 6 << 2") == "bit_manipulation"


def test_glyph_codec_roundtrip():
    text = "Nine1Eight ⊏⚗⊐"
    glyphs = text_to_glyphs(text)
    assert glyphs_to_text(glyphs) == text
    bits = text_to_binary(text)
    assert binary_to_text(bits) == text

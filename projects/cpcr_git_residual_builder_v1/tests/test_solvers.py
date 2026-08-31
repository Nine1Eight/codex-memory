from cpcr_git_builder.solvers import (
    solve_any,
    solve_bit_manipulation,
    solve_cryptarithm,
    solve_numeric_expression,
    solve_numeral_system,
    solve_unit_conversion,
    solve_gravity,
)


def test_numeric_solver():
    r = solve_numeric_expression("What is 7 * 12?")
    assert r and r.answer == "84" and r.verified


def test_bit_solver():
    r = solve_bit_manipulation("Compute 6 << 2")
    assert r and r.answer == "24" and r.category == "bit_manipulation" and r.verified


def test_numeral_solver():
    r = solve_numeral_system("Convert binary 101101 to decimal")
    assert r and r.answer == "45"
    r2 = solve_numeral_system("Convert decimal 45 to binary")
    assert r2 and r2.answer == "101101"


def test_unit_solver():
    r = solve_unit_conversion("Convert 3 km to meter")
    assert r and r.answer == "3000"


def test_gravity_solver():
    r = solve_gravity("On Earth, what is the weight in newtons if mass is 5 kg?")
    assert r and r.answer == "49"


def test_cryptarithm_solver_small():
    r = solve_cryptarithm("Solve cryptarithm A + A = B. What is B?")
    assert r and r.verified and r.answer == "2"


def test_solve_any_priority():
    assert solve_any("Convert 1 hour to minute").answer == "60"

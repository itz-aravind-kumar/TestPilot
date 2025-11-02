import pytest
from impl import add_numbers

@pytest.mark.parametrize("num1, num2, expected_sum", [
    # Happy Path: Positive integers
    (1, 2, 3),
    (10, 20, 30),
    (100, 500, 600),

    # Happy Path: Negative integers
    (-1, -2, -3),
    (-10, -20, -30),
    (-100, -500, -600),

    # Happy Path: Mixed positive and negative integers (result positive)
    (5, -2, 3),
    (20, -10, 10),

    # Happy Path: Mixed positive and negative integers (result negative)
    (-5, 2, -3),
    (-20, 10, -10),

    # Happy Path: Mixed positive and negative integers (result zero)
    (7, -7, 0),
    (-15, 15, 0),

    # Boundary Values: Zero with positive
    (0, 5, 5),
    (5, 0, 5),

    # Boundary Values: Zero with negative
    (0, -5, -5),
    (-5, 0, -5),

    # Boundary Values: Two zeros
    (0, 0, 0),

    # Large Input: Large positive integers
    (1_000_000_000, 2_000_000_000, 3_000_000_000),
    (10**18, 10**18, 2 * 10**18),
    (2**63 - 1, 1, 2**63), # Simulating max 64-bit signed int + 1

    # Large Input: Large negative integers
    (-1_000_000_000, -2_000_000_000, -3_000_000_000),
    (-10**18, -10**18, -2 * 10**18),
    (-(2**63), -1, -(2**63 + 1)), # Simulating min 64-bit signed int - 1

    # Large Input: Large mixed integers
    (10**18, -5 * 10**17, 5 * 10**17),
    (-10**18, 5 * 10**17, -5 * 10**17),
    (10**100, -10**100, 0), # Very large numbers resulting in zero
])
def test_add_numbers_valid_inputs(num1: int, num2: int, expected_sum: int):
    """
    Tests the add_numbers function with a wide range of valid integer inputs,
    including positive, negative, zero, and very large numbers.
    This covers happy path and various boundary/edge cases for valid inputs.
    """
    result = add_numbers(num1, num2)
    assert result == expected_sum, \
        f"For add_numbers({num1}, {num2}), expected {expected_sum}, but got {result}"

@pytest.mark.parametrize("num1, num2, expected_error_type", [
    # Invalid input types: strings
    ("hello", 1, TypeError),
    (1, "world", TypeError),
    ("1", "2", TypeError),

    # Invalid input types: floats
    (1.5, 2, TypeError),
    (1, 2.5, TypeError),
    (3.14, 2.71, TypeError),

    # Invalid input types: other objects
    ([1, 2], 3, TypeError),
    (4, {"a": 1}, TypeError),
    (None, 5, TypeError),
    (6, True, TypeError), # Booleans are subclasses of int, so this might pass depending on impl
                          # If the function strictly checks for int, it should fail.
                          # Assuming strict type checking for this test.
])
def test_add_numbers_invalid_input_types(num1, num2, expected_error_type):
    """
    Tests the add_numbers function with invalid input types (non-integers)
    to ensure it raises the appropriate TypeError.
    """
    with pytest.raises(expected_error_type) as excinfo:
        add_numbers(num1, num2)
    # The exact error message might vary based on Python version or specific implementation,
    # but checking the type of error is robust.
    assert "must be integers" in str(excinfo.value).lower() or \
           "argument 'a' must be int" in str(excinfo.value).lower() or \
           "argument 'b' must be int" in str(excinfo.value).lower() or \
           "an integer is required" in str(excinfo.value).lower()


def test_add_numbers_missing_arguments():
    """
    Tests the add_numbers function when called with missing arguments (empty input),
    expecting a TypeError.
    """
    with pytest.raises(TypeError) as excinfo:
        add_numbers()
    assert "missing 2 required positional arguments" in str(excinfo.value) or \
           "missing a required argument: 'a'" in str(excinfo.value) or \
           "missing a required argument: 'num1'" in str(excinfo.value), \
           f"Expected TypeError for missing arguments, but got: {excinfo.value}"

def test_add_numbers_too_many_arguments():
    """
    Tests the add_numbers function when called with too many arguments,
    expecting a TypeError.
    """
    with pytest.raises(TypeError) as excinfo:
        add_numbers(1, 2, 3)
    assert "takes 2 positional arguments but 3 were given" in str(excinfo.value) or \
           "got an unexpected keyword argument" in str(excinfo.value), \
           f"Expected TypeError for too many arguments, but got: {excinfo.value}"

# Property-based tests (optional, requires 'hypothesis' library: pip install hypothesis)
# These tests provide a more exhaustive check by generating arbitrary inputs.
# Uncomment if hypothesis is installed and desired for even deeper testing.
# from hypothesis import given, strategies as st

# @given(st.integers(), st.integers())
# def test_add_numbers_commutative_property(a: int, b: int):
#     """
#     Tests the commutative property of addition (a + b == b + a) using Hypothesis
#     to generate arbitrary integer inputs.
#     """
#     result1 = add_numbers(a, b)
#     result2 = add_numbers(b, a)
#     assert result1 == result2, \
#         f"Commutative property failed: {a} + {b} = {result1}, but {b} + {a} = {result2}"

# @given(st.integers(), st.integers(), st.integers())
# def test_add_numbers_associative_property(a: int, b: int, c: int):
#     """
#     Tests the associative property of addition ((a + b) + c == a + (b + c))
#     using Hypothesis to generate arbitrary integer inputs.
#     """
#     result1 = add_numbers(add_numbers(a, b), c)
#     result2 = add_numbers(a, add_numbers(b, c))
#     assert result1 == result2, \
#         f"Associative property failed: ({a} + {b}) + {c} = {result1}, but {a} + ({b} + {c}) = {result2}"

# @given(st.integers())
# def test_add_numbers_identity_property(a: int):
#     """
#     Tests the identity property of addition (a + 0 == a) using Hypothesis
#     to generate arbitrary integer inputs.
#     """
#     assert add_numbers(a, 0) == a, f"Identity property failed: {a} + 0 != {a}"
#     assert add_numbers(0, a) == a, f"Identity property failed: 0 + {a} != {a}"
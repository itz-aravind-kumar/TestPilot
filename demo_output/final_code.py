def add_numbers(num1: int, num2: int) -> int:
    """
    Adds two integers and returns their sum.

    This function takes exactly two arguments, both of which must be integers.
    It handles positive and negative numbers.

    Args:
        num1: The first integer.
        num2: The second integer.

    Returns:
        The sum of the two integers.

    Raises:
        TypeError: If either num1 or num2 is not an integer (explicitly excluding booleans).
    """
    # Validate num1: Must be an integer and not a boolean.
    # Booleans are a subclass of int in Python, but the tests indicate they should
    # be treated as invalid types for this function.
    if not isinstance(num1, int) or isinstance(num1, bool):
        raise TypeError("Both inputs must be integers (not booleans). "
                        f"Received type {type(num1).__name__} for num1.")

    # Validate num2: Must be an integer and not a boolean.
    if not isinstance(num2, int) or isinstance(num2, bool):
        raise TypeError("Both inputs must be integers (not booleans). "
                        f"Received type {type(num2).__name__} for num2.")

    # If both inputs are valid integers, return their sum.
    return num1 + num2
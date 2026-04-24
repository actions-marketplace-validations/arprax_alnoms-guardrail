def quadratic_trap(n):
    """A simple O(N^2) trap to test the Alnoms Guardrail."""
    data = list(range(n))
    count = 0
    for x in data:
        if x in data:  # This is the O(N) membership check inside an O(N) loop
            count += 1
    return count
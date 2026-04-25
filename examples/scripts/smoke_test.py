# This is a simple smoke test to verify that the Alnoms Guardrail is working correctly.
# It contains a known O(N^2) pattern that should trigger the guardrail's detection and block the PR.
def quadratic_trap(n):
    """A simple O(N^2) trap to test the Alnoms Guardrail."""
    data = list(range(n))
    count = 0
    for x in data:
        if x in data:  # This is the O(N) membership check inside an O(N) loop
            count += 1
    return count
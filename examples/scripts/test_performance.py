def slow_function(items):
    # Alnoms should flag this nested loop
    for i in items:
        for j in items:
            print(i, j)
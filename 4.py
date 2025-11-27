def multiply_matrices(A, B):
    result = [[0 for _ in range(len(B[0]))] for _ in range(len(A))]

    for i in range(len(A)):
        for j in range(len(B[0])):
            for k in range(len(B)):
                # BUG: Indices are messed up.
                # Should be A[i][k] * B[k][j], but let's break it.
                result[i][j] += A[i][j] * B[k][j]  # IndexError likely

    return result


X = [[1, 2], [3, 4]]  # 2x2
Y = [[5, 6], [7, 8]]  # 2x2

print(multiply_matrices(X, Y))
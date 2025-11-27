def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)  # Corrected: use len() to get the number of elements in the list
    return total / count

data = [10, 20, 30]
print("Average is:", calculate_average(data))
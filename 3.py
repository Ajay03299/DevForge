counter = 0

def increment_counter():
    print(f"Current counter: {counter}")
    global counter  # Add this line to access the global variable 'counter'
    counter += 1

increment_counter()
increment_counter()
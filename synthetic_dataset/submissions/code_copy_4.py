def find_factorial_val(input_num):
    if input_num < 0:
        raise ValueError("Cannot calculate factorial of negative input")
    if input_num == 0 or input_num == 1:
        return 1
    return input_num * find_factorial_val(input_num - 1)

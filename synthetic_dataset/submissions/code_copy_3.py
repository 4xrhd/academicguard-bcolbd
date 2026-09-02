def get_greatest_common_divisor(number_x, number_y):
    while number_y != 0:
        temp_val = number_y
        number_y = number_x % number_y
        number_x = temp_val
    return number_x

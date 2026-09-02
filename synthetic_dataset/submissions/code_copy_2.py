def perform_bubble_sort(input_array):
    array_size = len(input_array)
    for outer_idx in range(array_size):
        for inner_idx in range(0, array_size - outer_idx - 1):
            if input_array[inner_idx] > input_array[inner_idx + 1]:
                temp_variable = input_array[inner_idx]
                input_array[inner_idx] = input_array[inner_idx + 1]
                input_array[inner_idx + 1] = temp_variable
    return input_array

def find_item_index(elements, value_to_find):
    start_pos = 0
    end_pos = len(elements) - 1
    while start_pos <= end_pos:
        middle_index = (start_pos + end_pos) // 2
        current_element = elements[middle_index]
        if current_element == value_to_find:
            return middle_index
        elif current_element < value_to_find:
            start_pos = middle_index + 1
        else:
            end_pos = middle_index - 1
    return -1

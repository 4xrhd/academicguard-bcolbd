def get_fib_seq(limit):
    if limit <= 0:
        return list()
    elif limit == 1:
        return [0]
    results_list = [0, 1]
    while len(results_list) < limit:
        sum_val = results_list[-1] + results_list[-2]
        results_list.append(sum_val)
    return results_list

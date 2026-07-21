import math

def sort_by_attr(items: list, values: list, attr: str):
    order = {value: i for i, value in enumerate(values)}
    items.sort(key=lambda x: order.get(getattr(x, attr), float("inf")))
    return items

def paged_list(items: list, size: int, page: int):
    count = len(items)
    if count <= size:
        return items, 0

    last_page = math.ceil(count / size) - 1

    if page < 0: page = 0
    if page > last_page: page = last_page

    start_index = page * size
    end_index = start_index + size

    return items[start_index:end_index], last_page

# if __name__ == '__main__':
#     print(paged_list([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16], 5, 10))

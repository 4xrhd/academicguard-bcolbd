"""
create_test_data.py — Generate synthetic test data for model testing.
Creates sample submissions with known similarity patterns.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

# Sample student submissions with varying similarity levels
SUBMISSIONS = [
    {
        "student_id": "2021-1-60-001",
        "student_name": "Alice Johnson",
        "text": """
Binary search is an efficient algorithm for finding an item from a sorted list of items.
It works by repeatedly dividing in half the portion of the list that could contain the item,
until you've narrowed down the possible locations to just one. The algorithm starts by
comparing the target value to the middle element of the array. If they are equal, the
position is returned. If the target is less than the middle element, the search continues
in the lower half, otherwise in the upper half.
        """,
        "code": """
def binary_search(arr, target):
    left = 0
    right = len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
        """
    },
    {
        "student_id": "2021-1-60-002",
        "student_name": "Bob Smith",
        "text": """
Binary search represents an efficient searching algorithm applicable to sorted arrays.
The methodology involves repeatedly dividing the search interval in half until the target
value is located or the interval becomes empty. Initially the algorithm compares the target
with the middle element. If equal the position is returned. If the target is smaller the
search proceeds in the left half otherwise the right half is examined.
        """,
        "code": """
def search_binary(array, value):
    low = 0
    high = len(array) - 1
    
    while low <= high:
        middle = (low + high) // 2
        if array[middle] == value:
            return middle
        elif array[middle] < value:
            low = middle + 1
        else:
            high = middle - 1
    return -1
        """
    },
    {
        "student_id": "2021-1-60-003",
        "student_name": "Carol Davis",
        "text": """
I implemented a linear search first because it's simpler to understand. Linear search
just goes through each element one by one until it finds what you're looking for.
It's not as fast as binary search but it works on unsorted lists which is useful.
The time complexity is O(n) because in the worst case you have to check every element.
        """,
        "code": """
def linear_search(data, target):
    for i in range(len(data)):
        if data[i] == target:
            return i
    return -1
        """
    },
    {
        "student_id": "2021-1-60-004",
        "student_name": "David Wilson",
        "text": """
Sorting algorithms arrange elements in a specific order. Bubble sort is one of the
simplest sorting algorithms. It works by repeatedly swapping adjacent elements if
they are in wrong order. The algorithm gets its name because smaller elements
bubble to the top of the list. Although simple, bubble sort is not efficient for
large datasets with O(n²) time complexity.
        """,
        "code": """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
        """
    },
    {
        "student_id": "2021-1-60-005",
        "student_name": "Eve Martinez",
        "text": """
Binary search is an efficient algorithm for finding an item from a sorted list of items.
It works by repeatedly dividing in half the portion of the list that could contain the item,
until you've narrowed down the possible locations to just one. The algorithm starts by
comparing the target value to the middle element of the array.
        """,
        "code": """
def binary_search(arr, target):
    left = 0
    right = len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
        """
    }
]

def main():
    output_path = Path("data/test_submissions.json")
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(SUBMISSIONS, f, indent=2)
    
    print(f"✓ Created {len(SUBMISSIONS)} test submissions")
    print(f"✓ Saved to {output_path}")
    print("\nExpected similarity patterns:")
    print("  - Student 001 & 002: HIGH text similarity (paraphrased)")
    print("  - Student 001 & 002: HIGH code similarity (renamed variables)")
    print("  - Student 001 & 005: VERY HIGH similarity (near-duplicate)")
    print("  - Student 003 & 004: LOW similarity (different topics)")

if __name__ == "__main__":
    main()

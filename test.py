from typing import Dict


def myfunc(a: int, b: int) -> Dict[str, str]:
    return {
        'a': str(a),
        'b': str(b)
    }


if __name__ == "__main__":
    print(myfunc(10, 12))

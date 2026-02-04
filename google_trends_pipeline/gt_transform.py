from datetime import datetime, timezone


def transform(raw_data: list):
    if not raw_data:
        print("No data to transform")
        return []

    transformed = []
    current_time = datetime.now(timezone.utc)

    for item in raw_data:
        transformed.append({
            "keyword_value": item["keyword_value"].lower().strip(),
            "search_volume": item["search_volume"],
            "trend_date": current_time
        })

    print(f"Transformed {len(transformed)} records")
    return transformed


if __name__ == "__main__":
    sample = [
        {"keyword_value": "Cat", "search_volume": 4},
        {"keyword_value": "And", "search_volume": 83}
    ]
    result = transform(sample)
    print(result)

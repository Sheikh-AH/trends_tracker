# pylint: disable=import-error
"""Google Trends ETL Pipeline"""
from gt_extract import extract
from gt_transform import transform
from gt_load import load


def handler(event, context):
    """The main handler for the Google Trends ETL pipeline."""
    print("=" * 50)
    print("Starting Google Trends Pipeline")
    print("=" * 50)

    # Extract
    raw_data = extract()

    if not raw_data:
        print("Pipeline stopped: No data extracted")
        return {
            "statusCode": 200,
            "body": "No keywords found"
        }

    # Transform
    transformed_data = transform(raw_data)

    if not transformed_data:
        print("Pipeline stopped: No data transformed")
        return {
            "statusCode": 200,
            "body": "No data transformed"
        }

    # Load
    load(transformed_data)

    print("=" * 50)
    print("Pipeline complete")
    print("=" * 50)

    return {
        "statusCode": 200,
        "body": f"Loaded {len(transformed_data)} records"
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    handler(None, None)

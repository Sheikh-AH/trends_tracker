from gt_extract import extract
from gt_transform import transform
from gt_load import load


def run_pipeline():
    print("=" * 50)
    print("Starting Google Trends Pipeline")
    print("=" * 50)

    # Extract
    raw_data = extract()

    if not raw_data:
        print("Pipeline stopped: No data extracted")
        return

    # Transform
    transformed_data = transform(raw_data)

    if not transformed_data:
        print("Pipeline stopped: No data transformed")
        return

    # Load
    load(transformed_data)

    print("=" * 50)
    print("Pipeline complete")
    print("=" * 50)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_pipeline()

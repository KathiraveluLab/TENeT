import os

def main():
    data_dir = os.getenv("DATA_DIR", "/data")
    print(f"Starting HDI computation using data in {data_dir}...")
    # TODO: Compute Healthcare Desert Index (HDI)
    print("Computation complete.")

if __name__ == "__main__":
    main()

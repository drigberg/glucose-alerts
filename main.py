import os
from pylibrelinkup import PyLibreLinkUp, GraphResponse
from dotenv import load_dotenv

def main():
    load_dotenv()

    client = PyLibreLinkUp(email=os.getenv("USERNAME"), password=os.getenv("PASSWORD"))

    print("\nAuthenticating...")

    client.authenticate()

    print("Fetching and parsing data...")

    response_json = client._get_graph_data_json("01a00a94-f06c-742d-b3ce-631da9d29cc1")
    parsed = GraphResponse.model_validate(response_json)

    # parsed.graph_data only has data with smoothed five-minute granularity!
    current = parsed.current
    
    print("Latest!", parsed.current)


if __name__ == "__main__":
    main()